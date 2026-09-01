#!/usr/bin/env python
import pathlib
import shutil

PROJECT_DIRECTORY = pathlib.Path.cwd().expanduser().resolve()


def _keep_recursive(root, keep):
    if root in keep:
        return

    for p in root.iterdir():
        if p.is_dir():
            _keep_recursive(p, keep)
        elif p not in keep:
            p.unlink()


def _remove_empty_dirs(root):
    dir_iter = root.iterdir()
    try:
        removed_any = False
        first = next(dir_iter)
        if first.is_dir():
            removed_any = _remove_empty_dirs(first)
        for p in dir_iter:
            if p.is_dir():
                removed_any = _remove_empty_dirs(p)

        # reconsider the current directory now that it's children have
        # been processed
        if removed_any:
            _remove_empty_dirs(root)
    except StopIteration:
        root.rmdir()
        return True


def filter_directory(directory, *keep_relpaths, remove_empty=True):
    keep = set()
    for relpath in keep_relpaths:
        relpath = pathlib.Path(relpath)
        if relpath.is_absolute():
            raise ValueError(f"Invalid argument, {relpath} is an absolute path.")
        keep.add(directory / relpath)

    _keep_recursive(directory, keep)
    if remove_empty:
        _remove_empty_dirs(directory)


def delete(*, abspath=None, relpath=None):
    target = None
    if abspath:
        target = pathlib.Path(abspath)

    if relpath:
        if target:
            raise ValueError(f"Invalid arguments, both abspath and relpath were passed.")
        target = PROJECT_DIRECTORY / relpath

    if not target:
        raise ValueError(f"Invalid arguments, abspath or relpath must be passed.")

    _rm_any(target)


def _rm_any(target: pathlib.Path):
    if target.is_file():
        target.unlink()
    elif target.is_dir():
        shutil.rmtree(target)
    else:
        raise ValueError(f"Invalid argument, {target} is not a file or directory.")


if __name__ == "__main__":
    single_file = "{{ cookiecutter.layout }}" == "single-file"
    if single_file:
        delete(relpath="src")
        delete(relpath="pyproject.toml")
        delete(relpath="tests/test_cli.py")
        delete(relpath="tests/test_cli_help.py")
        delete(relpath="tests/test_config.py")
        delete(relpath="tests/test_console.py")
        delete(relpath="tests/test_context.py")
        (PROJECT_DIRECTORY / "{{ cookiecutter.package_name }}").chmod(0o755)
    else:
        delete(relpath="{{ cookiecutter.package_name }}")
        delete(relpath="tests/test_script.py")

    no_license = "{{ cookiecutter.open_source_license }}" == "None"
    if no_license:
        delete(relpath="LICENSE")
