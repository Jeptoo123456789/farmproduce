import os
import tempfile
import unittest

from backend.database import database_url


class DatabaseURLTests(unittest.TestCase):
    def test_default_database_uses_temp_dir_when_no_env_var_is_set(self):
        os.environ.pop("DATABASE_URL", None)
        url = database_url()
        self.assertIn("sqlite", url)
        self.assertIn(tempfile.gettempdir().replace("\\", "/"), url.replace("\\", "/"))


if __name__ == "__main__":
    unittest.main()
