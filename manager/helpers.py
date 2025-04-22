import os


def get_folder_path(instance):
    return  (os.path.join(instance.parent.path, instance.name + f"-{instance.id}")
                    if instance.parent else instance.name + f"-{instance.id}")

def get_document_path(instance):
    return os.path.join(instance.folder.name + f"-{instance.folder.id}", instance.name + f"-{instance.id}")