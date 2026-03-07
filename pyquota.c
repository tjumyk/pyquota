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

#include <errno.h>
#include <string.h>
#include <sys/quota.h>
#include <linux/quota.h> // still required for relatively old kernels

/* Fallbacks when build env has older kernel headers (e.g. manylinux); values match uapi/linux/quota.h */
#ifndef DQF_ROOT_SQUASH
#define DQF_ROOT_SQUASH (1 << 0)
#endif
#ifndef DQF_SYS_FILE
#define DQF_SYS_FILE (1 << 16)
#endif

#define SUBCMD(cmd) ((cmd) >> SUBCMDSHIFT)
#define ERRMSG_BUF_SIZE 256

PyDoc_STRVAR(moduleDoc, "Python wrapper for Linux quotactl(2). See man 2 quotactl.");

/* Docstrings for help(); see man 2 quotactl for full semantics. */
PyDoc_STRVAR(doc_quota_on, "quota_on(device, format, quota_file) -> None\n\nTurn on quotas (Q_QUOTAON). device: block device path. format: QFMT_VFS_OLD|QFMT_VFS_V0|QFMT_VFS_V1. quota_file: path to aquota.user|group|project. Requires CAP_SYS_ADMIN.");
PyDoc_STRVAR(doc_quota_off, "quota_off(device) -> None\n\nTurn off quotas (Q_QUOTAOFF) for device. Requires CAP_SYS_ADMIN.");
PyDoc_STRVAR(doc_get_quota, "get_quota(device, id) -> (bhard, bsoft, curspace, ihard, isoft, curinodes, btime, itime)\n\nGet quota (Q_GETQUOTA). Returns only when kernel reports full data (dqb_valid == QIF_ALL). Block limits in 1024-byte blocks; curspace in bytes; btime/itime Unix timestamps.");
PyDoc_STRVAR(doc_get_quota_partial, "get_quota_partial(device, id) -> (bhard, bsoft, curspace, ihard, isoft, curinodes, btime, itime, valid)\n\nGet quota allowing partial kernel data. valid (QIF_* bits) indicates which fields are set. See man 2 quotactl struct dqblk.");
PyDoc_STRVAR(doc_get_next_quota, "get_next_quota(device, id) -> (bhard, bsoft, curspace, ihard, isoft, curinodes, btime, itime, id)\n\nNext ID >= id with active quota (Q_GETNEXTQUOTA, kernel 4.6+). Requires dqb_valid == QIF_ALL.");
PyDoc_STRVAR(doc_get_next_quota_partial, "get_next_quota_partial(device, id) -> (..., id, valid)\n\nLike get_next_quota but allows partial data; last element is dqb_valid (QIF_*).");
PyDoc_STRVAR(doc_set_quota, "set_quota(device, id, block_hard, block_soft, inode_hard, inode_soft) -> None\n\nSet quota limits (Q_SETQUOTA). Block limits in 1024-byte blocks. Requires CAP_SYS_ADMIN.");
PyDoc_STRVAR(doc_get_info, "get_quota_info(device) -> (block_grace, inode_grace, flags)\n\nGet quotafile info (Q_GETINFO). Returns only when dqi_valid == IIF_ALL. Grace times in seconds; flags are DQF_* bits.");
PyDoc_STRVAR(doc_get_info_partial, "get_quota_info_partial(device) -> (block_grace, inode_grace, flags, valid)\n\nGet quotafile info allowing partial data. valid (IIF_* bits) indicates which fields are set. See man 2 quotactl struct dqinfo.");
PyDoc_STRVAR(doc_set_info, "set_quota_info(device, block_grace, inode_grace, flags) -> None\n\nSet quotafile info (Q_SETINFO). Requires CAP_SYS_ADMIN.");
PyDoc_STRVAR(doc_get_fmt, "get_quota_format(device) -> int\n\nGet quota format (Q_GETFMT). Returns QFMT_VFS_OLD, QFMT_VFS_V0, or QFMT_VFS_V1.");
PyDoc_STRVAR(doc_sync, "sync_quotas(device) -> None\n\nSync quota usages to disk (Q_SYNC). device=None syncs all filesystems with active quotas.");

static PyObject *APIError;
static PyObject *PermissionError;
static PyObject *NotFoundError;
static PyObject *InvalidError;

/* Set exception with message and errno attribute. exc_type is one of APIError, PermissionError, etc. */
static void setApiErrorEx(PyObject *exc_type, const char *msg, int errnum) {
    PyObject *exc = PyObject_CallFunction(exc_type, "s", msg);
    if (!exc)
        return;
    PyObject *errno_obj = PyLong_FromLong(errnum);
    if (errno_obj) {
        PyObject_SetAttrString(exc, "errno", errno_obj);
        Py_DECREF(errno_obj);
    }
    PyErr_SetObject(exc_type, exc);
    Py_DECREF(exc);
}

#define setApiError(msg, errnum) setApiErrorEx(APIError, (msg), (errnum))

/* Error messages aligned with quotactl(2) ERRORS. Raises PermissionError, NotFoundError, InvalidError, or APIError. */
static void handleError(int cmd) {
    int saved_errno = errno;
    const char *msg;
    PyObject *exc_type = APIError;

    switch (saved_errno) {
        case EPERM:
            exc_type = PermissionError;
            msg = "Caller lacks required privilege (CAP_SYS_ADMIN)";
            break;
        case ENOENT:
            exc_type = NotFoundError;
            msg = "Device or specified file does not exist";
            break;
        case ESRCH:
            exc_type = NotFoundError;
            switch (SUBCMD(cmd)) {
                case Q_QUOTAON:
                    msg = "Specified quota format was not found";
                    break;
#ifdef Q_GETNEXTQUOTA
                case Q_GETNEXTQUOTA:
                    msg = "No ID greater than or equal to the given ID has an active quota";
                    break;
#endif
                default:
                    msg = "No disk quota for the indicated user, group, or project; or quotas are not turned on for this filesystem";
                    break;
            }
            break;
        case EACCES:
            msg = "Quota file exists but is not a regular file or is not on the device filesystem";
            exc_type = InvalidError;
            break;
        case EBUSY:
            msg = "Another Q_QUOTAON has already been performed";
            exc_type = InvalidError;
            break;
        case EFAULT:
            msg = "Invalid device path or data buffer address";
            exc_type = InvalidError;
            break;
        case EINVAL:
            msg = (SUBCMD(cmd) == Q_QUOTAON) ? "Specified quota file is corrupted"
                                              : "Operation or quota type is invalid";
            exc_type = InvalidError;
            break;
        case ENOSYS:
            msg = "Kernel has not been compiled with CONFIG_QUOTA";
            exc_type = InvalidError;
            break;
        case ENOTBLK:
            msg = "Device is not a block device";
            exc_type = InvalidError;
            break;
        case ERANGE:
            msg = "Specified limits are out of the range allowed by the quota format";
            exc_type = InvalidError;
            break;
        default: {
            char buf[ERRMSG_BUF_SIZE];
            strerror_r(saved_errno, buf, sizeof(buf));
            setApiErrorEx(APIError, buf, saved_errno);
            return;
        }
    }
    setApiErrorEx(exc_type, msg, saved_errno);
}

/* Input validation: set ValueError and return NULL if invalid. */
static int validate_device(const char *device) {
    if (!device || device[0] == '\0') {
        PyErr_SetString(PyExc_ValueError, "device path cannot be empty");
        return -1;
    }
    return 0;
}

static int validate_device_and_id(const char *device, int id) {
    if (validate_device(device) != 0)
        return -1;
    if (id < 0) {
        PyErr_SetString(PyExc_ValueError, "user/group/project id must be non-negative");
        return -1;
    }
    return 0;
}

// Internal methods

static PyObject *quotaOn(int cmdType, PyObject *args) {
    const char *device;
    const int format;
    const char *quotaFile;

    if (!PyArg_ParseTuple(args, "sis", &device, &format, &quotaFile))
        return NULL;
    if (validate_device(device) != 0 || !quotaFile || quotaFile[0] == '\0') {
        if (!PyErr_Occurred())
            PyErr_SetString(PyExc_ValueError, "quota file path cannot be empty");
        return NULL;
    }

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
    if (validate_device(device) != 0)
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
    if (validate_device_and_id(device, unitId) != 0)
        return NULL;

    int cmd = QCMD(Q_GETQUOTA, cmdType);
    if (quotactl(cmd, device, unitId, (caddr_t) &data) != 0) {
        handleError(cmd);
        return NULL;
    }

    if (data.dqb_valid != QIF_ALL) {
        setApiError("Invalid quota data: kernel returned incomplete or invalid quota structure (dqb_valid != QIF_ALL)", 0);
        return NULL;
    }

    return Py_BuildValue("KKKKKKKK", data.dqb_bhardlimit, data.dqb_bsoftlimit, data.dqb_curspace,
                         data.dqb_ihardlimit, data.dqb_isoftlimit, data.dqb_curinodes, data.dqb_btime, data.dqb_itime);
}

static PyObject *getQuotaPartial(int cmdType, PyObject *args) {
    const char *device;
    const int unitId;
    struct dqblk data;

    if (!PyArg_ParseTuple(args, "si", &device, &unitId))
        return NULL;
    if (validate_device_and_id(device, unitId) != 0)
        return NULL;

    int cmd = QCMD(Q_GETQUOTA, cmdType);
    if (quotactl(cmd, device, unitId, (caddr_t) &data) != 0) {
        handleError(cmd);
        return NULL;
    }
    /* Partial quota: return 8 values + dqb_valid (QIF_* bits). Caller uses valid to know which fields are set. */
    return Py_BuildValue("KKKKKKKKI", data.dqb_bhardlimit, data.dqb_bsoftlimit, data.dqb_curspace,
                         data.dqb_ihardlimit, data.dqb_isoftlimit, data.dqb_curinodes, data.dqb_btime, data.dqb_itime,
                         (unsigned int)data.dqb_valid);
}

static PyObject *getNextQuota(int cmdType, PyObject *args) {
#ifdef Q_GETNEXTQUOTA
    const char *device;
    const int unitId; // ID of target user/group/project
    struct if_nextdqblk data; // The man page suggest using 'struct nextdqblk' but in fact only 'struct if_nextdqblk'
    // is defined in linux/quota.h

    if (!PyArg_ParseTuple(args, "si", &device, &unitId))
        return NULL;
    if (validate_device_and_id(device, unitId) != 0)
        return NULL;

    int cmd = QCMD(Q_GETNEXTQUOTA, cmdType);
    if (quotactl(cmd, device, unitId, (caddr_t) &data) != 0) {
        handleError(cmd);
        return NULL;
    }

    if (data.dqb_valid != QIF_ALL) {
        setApiError("Invalid quota data: kernel returned incomplete or invalid quota structure (dqb_valid != QIF_ALL)", 0);
        return NULL;
    }

    return Py_BuildValue("KKKKKKKKI", data.dqb_bhardlimit, data.dqb_bsoftlimit, data.dqb_curspace,
                         data.dqb_ihardlimit, data.dqb_isoftlimit, data.dqb_curinodes,
                         data.dqb_btime, data.dqb_itime, data.dqb_id);
}

static PyObject *getNextQuotaPartial(int cmdType, PyObject *args) {
    const char *device;
    const int unitId;
    struct if_nextdqblk data;

    if (!PyArg_ParseTuple(args, "si", &device, &unitId))
        return NULL;
    if (validate_device_and_id(device, unitId) != 0)
        return NULL;

    int cmd = QCMD(Q_GETNEXTQUOTA, cmdType);
    if (quotactl(cmd, device, unitId, (caddr_t) &data) != 0) {
        handleError(cmd);
        return NULL;
    }
    return Py_BuildValue("KKKKKKKKII", data.dqb_bhardlimit, data.dqb_bsoftlimit, data.dqb_curspace,
                         data.dqb_ihardlimit, data.dqb_isoftlimit, data.dqb_curinodes,
                         data.dqb_btime, data.dqb_itime, data.dqb_id, (unsigned int)data.dqb_valid);
}
#else
static PyObject *getNextQuota(int cmdType, PyObject *args) {
    (void)cmdType;
    (void)args;
    PyErr_SetString(APIError, "getNextQuota is not supported in the current kernel");
    return NULL;
}
static PyObject *getNextQuotaPartial(int cmdType, PyObject *args) {
    (void)cmdType;
    (void)args;
    PyErr_SetString(APIError, "get_next_*_quota_partial is not supported in the current kernel (requires 4.6+)");
    return NULL;
}
#endif

/* Q_SETQUOTA: dqb_valid indicates which entries have been set by the caller (man 2 quotactl).
 * We set only the four limits (QIF_LIMITS = QIF_BLIMITS | QIF_ILIMITS); usage and times are kernel-managed. */
static PyObject *setQuota(int cmdType, PyObject *args) {
    const char *device;
    const int unitId; // ID of target user/group/project
    const uint64_t bhardlimit, bsoftlimit, ihardlimit, isoftlimit;
    struct dqblk data;

    if (!PyArg_ParseTuple(args, "siKKKK", &device, &unitId, &bhardlimit, &bsoftlimit, &ihardlimit, &isoftlimit))
        return NULL;
    if (validate_device_and_id(device, unitId) != 0)
        return NULL;

    data.dqb_bhardlimit = bhardlimit;
    data.dqb_bsoftlimit = bsoftlimit;
    data.dqb_ihardlimit = ihardlimit;
    data.dqb_isoftlimit = isoftlimit;
    data.dqb_valid = QIF_LIMITS;  /* only limit fields set by caller */

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
    if (validate_device(device) != 0)
        return NULL;

    int cmd = QCMD(Q_GETINFO, cmdType);
    if (quotactl(cmd, device, 0, (caddr_t) &data) != 0) {
        handleError(cmd);
        return NULL;
    }

    if (data.dqi_valid != IIF_ALL) {
        setApiError("Invalid quota info: kernel returned incomplete or invalid dqinfo (dqi_valid != IIF_ALL)", 0);
        return NULL;
    }

    return Py_BuildValue("KKI", data.dqi_bgrace, data.dqi_igrace, data.dqi_flags);
}

static PyObject *getInfoPartial(int cmdType, PyObject *args) {
    const char *device;
    struct dqinfo data;

    if (!PyArg_ParseTuple(args, "s", &device))
        return NULL;
    if (validate_device(device) != 0)
        return NULL;

    int cmd = QCMD(Q_GETINFO, cmdType);
    if (quotactl(cmd, device, 0, (caddr_t) &data) != 0) {
        handleError(cmd);
        return NULL;
    }
    return Py_BuildValue("KKII", data.dqi_bgrace, data.dqi_igrace, data.dqi_flags, data.dqi_valid);
}

static PyObject *setInfo(int cmdType, PyObject *args) {
    const char *device;
    const uint64_t bgrace, igrace;
    const uint32_t flags;
    struct dqinfo data;

    if (!PyArg_ParseTuple(args, "sKKI", &device, &bgrace, &igrace, &flags))
        return NULL;
    if (validate_device(device) != 0)
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
    int format;  /* 4-byte buffer; kernel writes format number here (man 2 quotactl Q_GETFMT) */

    if (!PyArg_ParseTuple(args, "s", &device))
        return NULL;
    if (validate_device(device) != 0)
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
    if (device && device[0] == '\0') {
        PyErr_SetString(PyExc_ValueError, "device path cannot be empty");
        return NULL;
    }

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

static PyObject *getUserQuotaPartial(PyObject *self, PyObject *args) {
    return getQuotaPartial(USRQUOTA, args);
}

static PyObject *getNextUserQuota(PyObject *self, PyObject *args) {
    return getNextQuota(USRQUOTA, args);
}

static PyObject *getNextUserQuotaPartial(PyObject *self, PyObject *args) {
    return getNextQuotaPartial(USRQUOTA, args);
}

static PyObject *setUserQuota(PyObject *self, PyObject *args) {
    return setQuota(USRQUOTA, args);
}

static PyObject *getUserQuotaInfo(PyObject *self, PyObject *args) {
    return getInfo(USRQUOTA, args);
}

static PyObject *getUserQuotaInfoPartial(PyObject *self, PyObject *args) {
    return getInfoPartial(USRQUOTA, args);
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

static PyObject *getGroupQuotaPartial(PyObject *self, PyObject *args) {
    return getQuotaPartial(GRPQUOTA, args);
}

static PyObject *getNextGroupQuota(PyObject *self, PyObject *args) {
    return getNextQuota(GRPQUOTA, args);
}

static PyObject *getNextGroupQuotaPartial(PyObject *self, PyObject *args) {
    return getNextQuotaPartial(GRPQUOTA, args);
}

static PyObject *setGroupQuota(PyObject *self, PyObject *args) {
    return setQuota(GRPQUOTA, args);
}

static PyObject *getGroupQuotaInfo(PyObject *self, PyObject *args) {
    return getInfo(GRPQUOTA, args);
}

static PyObject *getGroupQuotaInfoPartial(PyObject *self, PyObject *args) {
    return getInfoPartial(GRPQUOTA, args);
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

static PyObject *getProjectQuotaPartial(PyObject *self, PyObject *args) {
#ifdef PRJQUOTA
    return getQuotaPartial(PRJQUOTA, args);
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

static PyObject *getNextProjectQuotaPartial(PyObject *self, PyObject *args) {
#ifdef PRJQUOTA
    return getNextQuotaPartial(PRJQUOTA, args);
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

static PyObject *getProjectQuotaInfoPartial(PyObject *self, PyObject *args) {
#ifdef PRJQUOTA
    return getInfoPartial(PRJQUOTA, args);
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
        {"user_quota_on",            userQuotaOn,           METH_VARARGS, doc_quota_on},
        {"user_quota_off",           userQuotaOff,          METH_VARARGS, doc_quota_off},
        {"get_user_quota",           getUserQuota,         METH_VARARGS, doc_get_quota},
        {"get_user_quota_partial", getUserQuotaPartial, METH_VARARGS, doc_get_quota_partial},
        {"get_next_user_quota",      getNextUserQuota,      METH_VARARGS, doc_get_next_quota},
        {"get_next_user_quota_partial", getNextUserQuotaPartial, METH_VARARGS, doc_get_next_quota_partial},
        {"set_user_quota",           setUserQuota,          METH_VARARGS, doc_set_quota},
        {"get_user_quota_info",      getUserQuotaInfo,      METH_VARARGS, doc_get_info},
        {"get_user_quota_info_partial", getUserQuotaInfoPartial, METH_VARARGS, doc_get_info_partial},
        {"set_user_quota_info",      setUserQuotaInfo,      METH_VARARGS, doc_set_info},
        {"get_user_quota_format",    getUserQuotaFormat,    METH_VARARGS, doc_get_fmt},
        {"sync_user_quotas",         syncUserQuotas,        METH_VARARGS, doc_sync},

        {"group_quota_on",           groupQuotaOn,          METH_VARARGS, doc_quota_on},
        {"group_quota_off",          groupQuotaOff,         METH_VARARGS, doc_quota_off},
        {"get_group_quota",          getGroupQuota,         METH_VARARGS, doc_get_quota},
        {"get_group_quota_partial", getGroupQuotaPartial, METH_VARARGS, doc_get_quota_partial},
        {"get_next_group_quota",     getNextGroupQuota,     METH_VARARGS, doc_get_next_quota},
        {"get_next_group_quota_partial", getNextGroupQuotaPartial, METH_VARARGS, doc_get_next_quota_partial},
        {"set_group_quota",          setGroupQuota,         METH_VARARGS, doc_set_quota},
        {"get_group_quota_info",     getGroupQuotaInfo,     METH_VARARGS, doc_get_info},
        {"get_group_quota_info_partial", getGroupQuotaInfoPartial, METH_VARARGS, doc_get_info_partial},
        {"set_group_quota_info",     setGroupQuotaInfo,     METH_VARARGS, doc_set_info},
        {"get_group_quota_format",   getGroupQuotaFormat,   METH_VARARGS, doc_get_fmt},
        {"sync_group_quotas",        syncGroupQuotas,       METH_VARARGS, doc_sync},

        {"project_quota_on",         projectQuotaOn,        METH_VARARGS, doc_quota_on},
        {"project_quota_off",        projectQuotaOff,       METH_VARARGS, doc_quota_off},
        {"get_project_quota",        getProjectQuota,       METH_VARARGS, doc_get_quota},
        {"get_project_quota_partial", getProjectQuotaPartial, METH_VARARGS, doc_get_quota_partial},
        {"get_next_project_quota",   getNextProjectQuota,   METH_VARARGS, doc_get_next_quota},
        {"get_next_project_quota_partial", getNextProjectQuotaPartial, METH_VARARGS, doc_get_next_quota_partial},
        {"set_project_quota",        setProjectQuota,       METH_VARARGS, doc_set_quota},
        {"get_project_quota_info",   getProjectQuotaInfo,   METH_VARARGS, doc_get_info},
        {"get_project_quota_info_partial", getProjectQuotaInfoPartial, METH_VARARGS, doc_get_info_partial},
        {"set_project_quota_info",   setProjectQuotaInfo,   METH_VARARGS, doc_set_info},
        {"get_project_quota_format", getProjectQuotaFormat, METH_VARARGS, doc_get_fmt},
        {"sync_project_quotas",      syncProjectQuotas,     METH_VARARGS, doc_sync},

        {NULL, NULL, 0, NULL}
};

static PyModuleDef moduleDef = {
        PyModuleDef_HEAD_INIT,
        "_native",  /* built as pyquota._native */
        moduleDoc,
        -1,
        methodDefs
};


PyMODINIT_FUNC PyInit__native(void) {
    PyObject *module;

    module = PyModule_Create(&moduleDef);
    if (module == NULL) {
        return NULL;
    }

    // register custom exceptions (hierarchy: APIError base; PermissionError, NotFoundError, InvalidError subclasses)
    APIError = PyErr_NewException("pyquota.APIError", NULL, NULL);
    Py_INCREF(APIError);
    PyModule_AddObject(module, "APIError", APIError);
    PermissionError = PyErr_NewException("pyquota.PermissionError", APIError, NULL);
    Py_INCREF(PermissionError);
    PyModule_AddObject(module, "PermissionError", PermissionError);
    NotFoundError = PyErr_NewException("pyquota.NotFoundError", APIError, NULL);
    Py_INCREF(NotFoundError);
    PyModule_AddObject(module, "NotFoundError", NotFoundError);
    InvalidError = PyErr_NewException("pyquota.InvalidError", APIError, NULL);
    Py_INCREF(InvalidError);
    PyModule_AddObject(module, "InvalidError", InvalidError);

    // quota format and quotafile flags (man 2 quotactl)
    PyModule_AddIntMacro(module, QFMT_VFS_OLD);
    PyModule_AddIntMacro(module, QFMT_VFS_V0);
    PyModule_AddIntMacro(module, QFMT_VFS_V1);
    PyModule_AddIntMacro(module, DQF_ROOT_SQUASH);
    PyModule_AddIntMacro(module, DQF_SYS_FILE);

    // dqb_valid bits (man 2 quotactl struct dqblk): which quota fields are valid
    PyModule_AddIntMacro(module, QIF_BLIMITS);
    PyModule_AddIntMacro(module, QIF_SPACE);
    PyModule_AddIntMacro(module, QIF_ILIMITS);
    PyModule_AddIntMacro(module, QIF_INODES);
    PyModule_AddIntMacro(module, QIF_BTIME);
    PyModule_AddIntMacro(module, QIF_ITIME);
    PyModule_AddIntMacro(module, QIF_LIMITS);
    PyModule_AddIntMacro(module, QIF_USAGE);
    PyModule_AddIntMacro(module, QIF_TIMES);
    PyModule_AddIntMacro(module, QIF_ALL);

    // dqi_valid bits (man 2 quotactl struct dqinfo): which quotafile info fields are valid
    PyModule_AddIntMacro(module, IIF_BGRACE);
    PyModule_AddIntMacro(module, IIF_IGRACE);
    PyModule_AddIntMacro(module, IIF_FLAGS);
    PyModule_AddIntMacro(module, IIF_ALL);

    // errno constants (for APIError.errno); see quotactl(2) ERRORS
    PyModule_AddIntMacro(module, EACCES);
    PyModule_AddIntMacro(module, EBUSY);
    PyModule_AddIntMacro(module, EFAULT);
    PyModule_AddIntMacro(module, EINVAL);
    PyModule_AddIntMacro(module, ENOENT);
    PyModule_AddIntMacro(module, ENOSYS);
    PyModule_AddIntMacro(module, ENOTBLK);
    PyModule_AddIntMacro(module, EPERM);
    PyModule_AddIntMacro(module, ERANGE);
    PyModule_AddIntMacro(module, ESRCH);

    return module;
}