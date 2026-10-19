## 🔨 Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/JuanVilla424/ai18n.git
   ```

2. **Navigate to the Project Directory**

   ```bash
   cd ai18n
   ```

3. **Set up the environment**

   ```bash
   git submodule update --init
   python -m venv .venv
   .venv/bin/pip install -r requirements.txt
   .venv/bin/pip install -r requirements.dev.txt
   .venv/bin/pre-commit install --hook-type pre-commit --hook-type pre-push
   ```

4. **Check that everything works**

   ```bash
   .venv/bin/pytest
   .venv/bin/python src/ai18n.py check
   ```

## 🧩 Using ai18n from another repository

Vendor this repository as a submodule and call the resolver from it:

```bash
git submodule add -b dev https://github.com/JuanVilla424/ai18n.git helpers/ai18n
python3 helpers/ai18n/src/ai18n.py show --root .
```

The host repository declares the runtime dependencies of the resolver, `PyYAML` and `jsonschema`,
in its own requirements.
