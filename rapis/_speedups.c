#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <string.h>

static PyObject *parse_qsl, *qsl_kwargs;

static int
hexval(Py_UCS1 c)
{
    if (c >= '0' && c <= '9')
        return c - '0';
    if (c >= 'a' && c <= 'f')
        return c - 'a' + 10;
    if (c >= 'A' && c <= 'F')
        return c - 'A' + 10;
    return -1;
}

static PyObject *
unquote(PyObject *qs, const Py_UCS1 *s, Py_ssize_t start, Py_ssize_t end)
{
    Py_ssize_t n = end - start, m = 0;
    if (!memchr(s + start, '%', n) && !memchr(s + start, '+', n))
        return PyUnicode_Substring(qs, start, end);
    char stack[256];
    char *buf = n <= (Py_ssize_t)sizeof(stack) ? stack : PyMem_Malloc(n);
    if (buf == NULL)
        return PyErr_NoMemory();
    for (Py_ssize_t i = start; i < end; i++) {
        int hi, lo;
        if (s[i] == '%' && end - i > 2 && (hi = hexval(s[i + 1])) >= 0
                && (lo = hexval(s[i + 2])) >= 0) {
            buf[m++] = (char)(hi << 4 | lo);
            i += 2;
        }
        else {
            buf[m++] = s[i] == '+' ? ' ' : (char)s[i];
        }
    }
    PyObject *out = PyUnicode_DecodeUTF8(buf, m, "replace");
    if (buf != stack)
        PyMem_Free(buf);
    return out;
}

static PyObject *
parse_query(PyObject *module, PyObject *qs)
{
    if (!PyUnicode_Check(qs)) {
        PyErr_SetString(PyExc_TypeError, "query string must be str");
        return NULL;
    }
    PyObject *out = PyDict_New();
    if (out == NULL)
        return NULL;
    if (!PyUnicode_IS_ASCII(qs)) {
        PyObject *pairs = PyObject_VectorcallDict(parse_qsl, &qs, 1, qsl_kwargs);
        int failed = pairs == NULL || PyDict_MergeFromSeq2(out, pairs, 1) < 0;
        Py_XDECREF(pairs);
        if (failed) {
            Py_DECREF(out);
            return NULL;
        }
        return out;
    }
    const Py_UCS1 *s = PyUnicode_1BYTE_DATA(qs);
    Py_ssize_t n = PyUnicode_GET_LENGTH(qs);
    for (Py_ssize_t start = 0, end; start < n; start = end + 1) {
        const Py_UCS1 *amp = memchr(s + start, '&', n - start);
        end = amp ? amp - s : n;
        if (end == start)
            continue;
        const Py_UCS1 *eq = memchr(s + start, '=', end - start);
        Py_ssize_t mid = eq ? eq - s : end;
        PyObject *key = unquote(qs, s, start, mid);
        PyObject *value = key ? unquote(qs, s, eq ? mid + 1 : end, end) : NULL;
        int failed = value == NULL || PyDict_SetItem(out, key, value) < 0;
        Py_XDECREF(key);
        Py_XDECREF(value);
        if (failed) {
            Py_DECREF(out);
            return NULL;
        }
    }
    return out;
}

static PyMethodDef methods[] = {
    {"parse_query", parse_query, METH_O, NULL},
    {NULL, NULL, 0, NULL},
};

static struct PyModuleDef module = {
    PyModuleDef_HEAD_INIT,
    .m_name = "rapis._speedups",
    .m_size = -1,
    .m_methods = methods,
};

PyMODINIT_FUNC
PyInit__speedups(void)
{
    PyObject *urllib_parse = PyImport_ImportModule("urllib.parse");
    if (urllib_parse == NULL)
        return NULL;
    parse_qsl = PyObject_GetAttrString(urllib_parse, "parse_qsl");
    Py_DECREF(urllib_parse);
    qsl_kwargs = Py_BuildValue("{s:O}", "keep_blank_values", Py_True);
    if (parse_qsl == NULL || qsl_kwargs == NULL)
        return NULL;
    PyObject *m = PyModule_Create(&module);
#ifdef Py_GIL_DISABLED
    if (m != NULL && PyUnstable_Module_SetGIL(m, Py_MOD_GIL_NOT_USED) < 0) {
        Py_DECREF(m);
        return NULL;
    }
#endif
    return m;
}
