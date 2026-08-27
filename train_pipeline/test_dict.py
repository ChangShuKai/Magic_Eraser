import modal
d = modal.Dict.from_name('test-dict', create_if_missing=True)
d['test'] = 1
print(d['test'])
