import importlib


def find_class_in_module(target_cls_name, module):
    target_cls_name = target_cls_name.replace("_", "").lower()
    clslib = importlib.import_module(module)
    cls = None
    for name, clsobj in clslib.__dict__.items():
        if name.lower() == target_cls_name:
            cls = clsobj

    if cls is None:
        print(
            f"In {module}, there should be a class whose name matches "
            f"{target_cls_name} in lowercase without underscore(_)"
        )
        exit(0)

    return cls


def multiply(a, b):
    return a * b


def divide(a, b):
    return a / b


def without_key(d, *keys):
    """ Return a dict without specified keys.
    WARNING: modifies the existing dict. Copying is expensive.

    Args:
        d (Dictionary):
    """
    for k in keys:
        d.pop(k)
    return d


def get_prev_data_zero_bounded(data, end_idx, num_frames):
    start_idx = end_idx - num_frames
    prev_n_data = data[max(0, start_idx) : end_idx]
    if start_idx < 0:
        prepend_dupes = [data[0] for _ in range(abs(start_idx))]
        prev_n_data = prepend_dupes + prev_n_data
    return prev_n_data