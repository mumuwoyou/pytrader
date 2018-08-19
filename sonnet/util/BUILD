# Description:
#   Utilities for cyvn.cyvn.sonnet.

package(default_visibility = ["//visibility:public"])

licenses(["notice"])  # Apache 2.0 License

exports_files(["LICENSE"])

py_binary(
    name = "migrate_checkpoint",
    srcs = ["migrate_checkpoint.py"],
    deps = [
        "//cyvn.cyvn.sonnet",  # build_cleaner:keep
        # tensorflow dep,
    ],
)
