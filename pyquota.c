#define PY_SSIZE_T_CLEAN

#include <Python.h>

/* The minimal supported kernel is 2.4.22, which includes the definition of
 *   - struct dqblk
 *   - struct dqinfo
 *   - Q_GETINFO
 *   - Q_SETINFO
 *   - Q_GETFMT
 * and removes support for
 *   - Q_GETSTATS
 *
 * PRJQUOTA is supported if the kernel is at least 4.1.
 * Q_GETNEXTQUOTA is supported if the kernel is at least 4.6.
 *
 * Currently, apis for XFS are not supported due to lack of documentation and testing environments.
 */
#include <linux/version.h>
#if LINUX_VERSION_CODE < KERNEL_VERSION(2, 4, 22)
#error "Minimal supported kernel is 2.4.22"
#endif

#include <sys/quota.h>
#include <linux/quota.h> // still required for relatively old kernels

#define SUBCMD(cmd) ((cmd) >> SUBCMDSHIFT)

PyDoc_STRVAR(moduleDoc, "PyQuota is a simple python wrapper for C apis of quotactl.");

static PyObject *APIError;

// Better error handling than PyErr_SetFromErrno(errno)
static void handleError(int cmd) {
    switch (errno) {
        case EACCES:
            // cmd should be Q_QUOTAON
            PyErr_SetString(APIError, "Quota file exists but is not a regular file or not on the specified filesystem");
            break;
        case EBUSY:
            // cmd should be Q_QUOTAON
            PyErr_SetString(APIError, "Another quotaOn command has been performed");
            break;
        case EFAULT:
            PyErr_SetString(APIError, "Invalid device path or data buffer");
            break;
        case EINVAL:
            if (SUBCMD(cmd) == Q_QUOTAON)
                PyErr_SetString(APIError, "Quota file is corrupted");
            else
                PyErr_SetString(APIError, "Command or quota type is invalid");
            break;
        case ENOENT:
            PyErr_SetString(APIError, "Device or file does not exist");
            break;
        case ENOSYS:
            PyErr_SetString(APIError, "The kernel has not been compiled with the CONFIG_QUOTA option");
            break;
        case ENOTBLK:
            PyErr_SetString(APIError, "Device is not a block device");
            break;
        case EPERM:
            PyErr_SetString(APIError, "Privilege required");
            break;
        case ERANGE:
            // cmd should be Q_SETQUOTA
            PyErr_SetString(APIError, "Specified limits are out of the range allowed by the quota format");
            break;
        case ESRCH:
            switch (SUBCMD(cmd)) {
                case Q_QUOTAON:
                    PyErr_SetString(APIError, "Quota format was not found");
                    break;
#ifdef Q_GETNEXTQUOTA
                case Q_GETNEXTQUOTA:
                    PyErr_SetString(APIError,
                                    "There is no ID greater than or equal to the specified id that has an active quota");
                    break;
#endif
                default:
                    PyErr_SetString(APIError,
                                    "No disk quota found for the indicated user/group/project or quotas have not been turned on for this filesystem");
            }
            break;
        default:
            PyErr_SetString(APIError, "Unknown error");
    }
}

// Internal methods

static PyObject *quotaOn(int cmdType, PyObject *args) {
    const char *device;
    const int format;
    const char *quotaFile;

    if (!PyArg_ParseTuple(args, "sis", &device, &format, &quotaFile))
        return NULL;

    int cmd = QCMD(Q_QUOTAON, cmdType);
    if (quotactl(cmd, device, format, (caddr_t) quotaFile) != 0) {
        handleError(cmd);
        return NULL;
    }
    Py_RETURN_NONE;
}

static PyObject *quotaOff(int cmdType, PyObject *args) {
    const char *device;

    if (!PyArg_ParseTuple(args, "s", &device))
        return NULL;

    int cmd = QCMD(Q_QUOTAOFF, cmdType);
    if (quotactl(cmd, device, 0, NULL) != 0) {
        handleError(cmd);
        return NULL;
    }
    Py_RETURN_NONE;
}

static PyObject *getQuota(int cmdType, PyObject *args) {
    const char *device;
    const int unitId; // ID of target user/group/project
    struct dqblk data;

    if (!PyArg_ParseTuple(args, "si", &device, &unitId))
        return NULL;

    int cmd = QCMD(Q_GETQUOTA, cmdType);
    if (quotactl(cmd, device, unitId, (caddr_t) &data) != 0) {
        handleError(cmd);
        return NULL;
    }

    if (data.dqb_valid != QIF_ALL) {
        PyErr_SetString(APIError, "Retrieved data is invalid");
        return NULL;
    }

    // 'K' for unsigned long long
    return Py_BuildValue("KKKKKKKK", data.dqb_bhardlimit, data.dqb_bsoftlimit, data.dqb_curspace,
                         data.dqb_ihardlimit, data.dqb_isoftlimit, data.dqb_curinodes, data.dqb_btime, data.dqb_itime);
}

static PyObject *getNextQuota(int cmdType, PyObject *args) {
#ifdef Q_GETNEXTQUOTA
    const char *device;
    const int unitId; // ID of target user/group/project
    struct if_nextdqblk data; // The man page suggest using 'struct nextdqblk' but in fact only 'struct if_nextdqblk'
    // is defined in linux/quota.h

    if (!PyArg_ParseTuple(args, "si", &device, &unitId))
        return NULL;

    int cmd = QCMD(Q_GETNEXTQUOTA, cmdType);
    if (quotactl(cmd, device, unitId, (caddr_t) &data) != 0) {
        handleError(cmd);
        return NULL;
    }

    if (data.dqb_valid != QIF_ALL) {
        PyErr_SetString(APIError, "Retrieved data is invalid");
        return NULL;
    }

    // 'K' for unsigned long long, 'I' for unsigned int
    return Py_BuildValue("KKKKKKKKI", data.dqb_bhardlimit, data.dqb_bsoftlimit, data.dqb_curspace,
                         data.dqb_ihardlimit, data.dqb_isoftlimit, data.dqb_curinodes,
                         data.dqb_btime, data.dqb_itime, data.dqb_id);
#else
    PyErr_SetString(APIError, "getNextQuota is not supported in the current kernel");
    return NULL;
#endif
}

static PyObject *setQuota(int cmdType, PyObject *args) {
    const char *device;
    const int unitId; // ID of target user/group/project
    const uint64_t bhardlimit, bsoftlimit, ihardlimit, isoftlimit;
    struct dqblk data;

    if (!PyArg_ParseTuple(args, "siKKKK", &device, &unitId, &bhardlimit, &bsoftlimit, &ihardlimit, &isoftlimit))
        return NULL;

    data.dqb_bhardlimit = bhardlimit;
    data.dqb_bsoftlimit = bsoftlimit;
    data.dqb_ihardlimit = ihardlimit;
    data.dqb_isoftlimit = isoftlimit;
    data.dqb_valid = QIF_LIMITS;

    int cmd = QCMD(Q_SETQUOTA, cmdType);
    if (quotactl(cmd, device, unitId, (caddr_t) &data) != 0) {
        handleError(cmd);
        return NULL;
    }
    Py_RETURN_NONE;
}

static PyObject *getInfo(int cmdType, PyObject *args) {
    const char *device;
    struct dqinfo data;

    if (!PyArg_ParseTuple(args, "s", &device))
        return NULL;

    int cmd = QCMD(Q_GETINFO, cmdType);
    if (quotactl(cmd, device, 0, (caddr_t) &data) != 0) {
        handleError(cmd);
        return NULL;
    }

    if (data.dqi_valid != IIF_ALL) {
        PyErr_SetString(APIError, "Retrieved data is invalid");
        return NULL;
    }

    // 'K' for unsigned long long, 'I' for unsigned int
    return Py_BuildValue("KKI", data.dqi_bgrace, data.dqi_igrace, data.dqi_flags);
}

static PyObject *setInfo(int cmdType, PyObject *args) {
    const char *device;
    const uint64_t bgrace, igrace;
    const uint32_t flags;
    struct dqinfo data;

    if (!PyArg_ParseTuple(args, "sKKI", &device, &bgrace, &igrace, &flags))
        return NULL;

    data.dqi_bgrace = bgrace;
    data.dqi_igrace = igrace;
    data.dqi_flags = flags;
    data.dqi_valid = IIF_ALL;

    int cmd = QCMD(Q_SETINFO, cmdType);
    if (quotactl(cmd, device, 0, (caddr_t) &data) != 0) {
        handleError(cmd);
        return NULL;
    }
    Py_RETURN_NONE;
}

static PyObject *getFmt(int cmdType, PyObject *args) {
    const char *device;
    const int format;

    if (!PyArg_ParseTuple(args, "s", &device))
        return NULL;

    int cmd = QCMD(Q_GETFMT, cmdType);
    if (quotactl(cmd, device, 0, (caddr_t) &format) != 0) {
        handleError(cmd);
        return NULL;
    }
    return PyLong_FromLong(format);
}

static PyObject *_sync(int cmdType, PyObject *args) { // use _sync() to avoid conflict with sync()
    const char *device;

    if (!PyArg_ParseTuple(args, "z", &device)) // device can be a str or None
        return NULL;

    int cmd = QCMD(Q_SYNC, cmdType);
    if (quotactl(cmd, device, 0, NULL) != 0) {
        handleError(cmd);
        return NULL;
    }
    Py_RETURN_NONE;
}

// public methods for user quotas
static PyObject *userQuotaOn(PyObject *self, PyObject *args) {
    return quotaOn(USRQUOTA, args);
}

static PyObject *userQuotaOff(PyObject *self, PyObject *args) {
    return quotaOff(USRQUOTA, args);
}

static PyObject *getUserQuota(PyObject *self, PyObject *args) {
    return getQuota(USRQUOTA, args);
}

static PyObject *getNextUserQuota(PyObject *self, PyObject *args) {
    return getNextQuota(USRQUOTA, args);
}

static PyObject *setUserQuota(PyObject *self, PyObject *args) {
    return setQuota(USRQUOTA, args);
}

static PyObject *getUserQuotaInfo(PyObject *self, PyObject *args) {
    return getInfo(USRQUOTA, args);
}

static PyObject *setUserQuotaInfo(PyObject *self, PyObject *args) {
    return setInfo(USRQUOTA, args);
}

static PyObject *getUserQuotaFormat(PyObject *self, PyObject *args) {
    return getFmt(USRQUOTA, args);
}

static PyObject *syncUserQuotas(PyObject *self, PyObject *args) {
    return _sync(USRQUOTA, args);
}


// public methods for group quotas
static PyObject *groupQuotaOn(PyObject *self, PyObject *args) {
    return quotaOn(GRPQUOTA, args);
}

static PyObject *groupQuotaOff(PyObject *self, PyObject *args) {
    return quotaOff(GRPQUOTA, args);
}

static PyObject *getGroupQuota(PyObject *self, PyObject *args) {
    return getQuota(GRPQUOTA, args);
}

static PyObject *getNextGroupQuota(PyObject *self, PyObject *args) {
    return getNextQuota(GRPQUOTA, args);
}

static PyObject *setGroupQuota(PyObject *self, PyObject *args) {
    return setQuota(GRPQUOTA, args);
}

static PyObject *getGroupQuotaInfo(PyObject *self, PyObject *args) {
    return getInfo(GRPQUOTA, args);
}

static PyObject *setGroupQuotaInfo(PyObject *self, PyObject *args) {
    return setInfo(GRPQUOTA, args);
}

static PyObject *getGroupQuotaFormat(PyObject *self, PyObject *args) {
    return getFmt(GRPQUOTA, args);
}

static PyObject *syncGroupQuotas(PyObject *self, PyObject *args) {
    return _sync(GRPQUOTA, args);
}

// public methods for project quotas
static PyObject *projectQuotaOn(PyObject *self, PyObject *args) {
#ifdef PRJQUOTA
    return quotaOn(PRJQUOTA, args);
#else
    PyErr_SetString(APIError, "Project quota is not supported in the current kernel");
    return NULL;
#endif
}

static PyObject *projectQuotaOff(PyObject *self, PyObject *args) {
#ifdef PRJQUOTA
    return quotaOff(PRJQUOTA, args);
#else
    PyErr_SetString(APIError, "Project quota is not supported in the current kernel");
    return NULL;
#endif
}

static PyObject *getProjectQuota(PyObject *self, PyObject *args) {
#ifdef PRJQUOTA
    return getQuota(PRJQUOTA, args);
#else
    PyErr_SetString(APIError, "Project quota is not supported in the current kernel");
    return NULL;
#endif
}

static PyObject *getNextProjectQuota(PyObject *self, PyObject *args) {
#ifdef PRJQUOTA
    return getNextQuota(PRJQUOTA, args);
#else
    PyErr_SetString(APIError, "Project quota is not supported in the current kernel");
    return NULL;
#endif
}

static PyObject *setProjectQuota(PyObject *self, PyObject *args) {
#ifdef PRJQUOTA
    return setQuota(PRJQUOTA, args);
#else
    PyErr_SetString(APIError, "Project quota is not supported in the current kernel");
    return NULL;
#endif
}

static PyObject *getProjectQuotaInfo(PyObject *self, PyObject *args) {
#ifdef PRJQUOTA
    return getInfo(PRJQUOTA, args);
#else
    PyErr_SetString(APIError, "Project quota is not supported in the current kernel");
    return NULL;
#endif
}

static PyObject *setProjectQuotaInfo(PyObject *self, PyObject *args) {
#ifdef PRJQUOTA
    return setInfo(PRJQUOTA, args);
#else
    PyErr_SetString(APIError, "Project quota is not supported in the current kernel");
    return NULL;
#endif
}

static PyObject *getProjectQuotaFormat(PyObject *self, PyObject *args) {
#ifdef PRJQUOTA
    return getFmt(PRJQUOTA, args);
#else
    PyErr_SetString(APIError, "Project quota is not supported in the current kernel");
    return NULL;
#endif
}

static PyObject *syncProjectQuotas(PyObject *self, PyObject *args) {
#ifdef PRJQUOTA
    return _sync(PRJQUOTA, args);
#else
    PyErr_SetString(APIError, "Project quota is not supported in the current kernel");
    return NULL;
#endif
}

static PyMethodDef methodDefs[] = {
        {"user_quota_on",            userQuotaOn,           METH_VARARGS, "Turn on user quotas for a filesystem"},
        {"user_quota_off",           userQuotaOff,          METH_VARARGS, "Turn off user quotas for a filesystem"},
        {"get_user_quota",           getUserQuota,          METH_VARARGS, "Get quota of a user on a filesystem"},
        {"get_next_user_quota",      getNextUserQuota,      METH_VARARGS, "Get quota of the next user, whose ID is greater than or equal to the specified ID, on a filesystem"},
        {"set_user_quota",           setUserQuota,          METH_VARARGS, "Set quota of a user on a filesystem"},
        {"get_user_quota_info",      getUserQuotaInfo,      METH_VARARGS, "Get information about the user quotafile for a filesystem"},
        {"set_user_quota_info",      setUserQuotaInfo,      METH_VARARGS, "Set information about the user quotafile for a filesystem"},
        {"get_user_quota_format",    getUserQuotaFormat,    METH_VARARGS, "Get quota format used for user quotas on a filesystem"},
        {"sync_user_quotas",         syncUserQuotas,        METH_VARARGS, "Update the on-disk copy of user quota usages for a filesystem or all filesystems with active quotas"},

        {"group_quota_on",           groupQuotaOn,          METH_VARARGS, "Turn on group quotas for a filesystem"},
        {"group_quota_off",          groupQuotaOff,         METH_VARARGS, "Turn off group quotas for a filesystem"},
        {"get_group_quota",          getGroupQuota,         METH_VARARGS, "Get quota of a group on a filesystem"},
        {"get_next_group_quota",     getNextGroupQuota,     METH_VARARGS, "Get quota of the next group, whose ID is greater than or equal to the specified ID, on a filesystem"},
        {"set_group_quota",          setGroupQuota,         METH_VARARGS, "Set quota of a group on a filesystem"},
        {"get_group_quota_info",     getGroupQuotaInfo,     METH_VARARGS, "Get information about the group quotafile for a filesystem"},
        {"set_group_quota_info",     setGroupQuotaInfo,     METH_VARARGS, "Set information about the group quotafile for a filesystem"},
        {"get_group_quota_format",   getGroupQuotaFormat,   METH_VARARGS, "Get quota format used for group quotas on a filesystem"},
        {"sync_group_quotas",        syncGroupQuotas,       METH_VARARGS, "Update the on-disk copy of group quota usages for a filesystem or all filesystems with active quotas"},

        {"project_quota_on",         projectQuotaOn,        METH_VARARGS, "Turn on project quotas for a filesystem"},
        {"project_quota_off",        projectQuotaOff,       METH_VARARGS, "Turn off project quotas for a filesystem"},
        {"get_project_quota",        getProjectQuota,       METH_VARARGS, "Get quota of a project on a filesystem"},
        {"get_next_project_quota",   getNextProjectQuota,   METH_VARARGS, "Get quota of the next project, whose ID is greater than or equal to the specified ID, on a filesystem"},
        {"set_project_quota",        setProjectQuota,       METH_VARARGS, "Set quota of a project on a filesystem"},
        {"get_project_quota_info",   getProjectQuotaInfo,   METH_VARARGS, "Get information about the project quotafile for a filesystem"},
        {"set_project_quota_info",   setProjectQuotaInfo,   METH_VARARGS, "Set information about the project quotafile for a filesystem"},
        {"get_project_quota_format", getProjectQuotaFormat, METH_VARARGS, "Get quota format used for project quotas on a filesystem"},
        {"sync_project_quotas",      syncProjectQuotas,     METH_VARARGS, "Update the on-disk copy of project quota usages for a filesystem or all filesystems with active quotas"},

        {NULL, NULL, 0, NULL} // sentinel
};

static PyModuleDef moduleDef = {
        PyModuleDef_HEAD_INIT,
        "pyquota",
        moduleDoc,
        -1,
        methodDefs
};


PyMODINIT_FUNC PyInit_pyquota(void) {
    PyObject *module;

    module = PyModule_Create(&moduleDef);
    if (module == NULL) {
        return NULL;
    }

    // register custom exceptions
    APIError = PyErr_NewException("pyquota.APIError", NULL, NULL);
    Py_INCREF(APIError);
    PyModule_AddObject(module, "APIError", APIError);

    // register constant numbers
    PyModule_AddObject(module, "QFMT_VFS_OLD", PyLong_FromLong(QFMT_VFS_OLD));
    PyModule_AddObject(module, "QFMT_VFS_V0", PyLong_FromLong(QFMT_VFS_V0));
    PyModule_AddObject(module, "QFMT_VFS_V1", PyLong_FromLong(QFMT_VFS_V1));
    PyModule_AddObject(module, "DQF_ROOT_SQUASH", PyLong_FromLong(DQF_ROOT_SQUASH));
    PyModule_AddObject(module, "DQF_SYS_FILE", PyLong_FromLong(DQF_SYS_FILE));

    return module;
}