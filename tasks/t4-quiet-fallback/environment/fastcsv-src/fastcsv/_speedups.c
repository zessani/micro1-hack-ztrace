#include <Python.h>
#include <zstd.h>

static PyObject *compressed_bound(PyObject *self, PyObject *arg) {
    Py_ssize_t n = PyLong_AsSsize_t(arg);
    if (n < 0 && PyErr_Occurred()) return NULL;
    return PyLong_FromSize_t(ZSTD_compressBound((size_t)n));
}

static PyMethodDef methods[] = {
    {"compressed_bound", compressed_bound, METH_O, "upper bound for compressed size"},
    {NULL, NULL, 0, NULL}};

static struct PyModuleDef mod = {PyModuleDef_HEAD_INIT, "_speedups", NULL, -1, methods};

PyMODINIT_FUNC PyInit__speedups(void) { return PyModule_Create(&mod); }
