from hatchling.metadata.plugin.interface import MetadataHookInterface


class CustomMetadataHook(MetadataHookInterface):

    def update(self, metadata):
        import importlib
        import os
        import sys

        path = os.path.join(self.root, "src", "memoria", "__about__.py")
        spec = importlib.util.spec_from_file_location("memoria.__about__", path)
        module = importlib.util.module_from_spec(spec)
        sys.modules['memoria.__about__'] = module
        spec.loader.exec_module(module)
        for attr in ("description", "authors"):
            metadata[attr] = getattr(module, f"__{attr}__")
