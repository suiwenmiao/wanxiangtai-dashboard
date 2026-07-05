PYTHON ?= python3
PNPM ?= pnpm

.PHONY: setup check login download data dev build package deploy daily preview clean

setup:
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m playwright install chromium
	cd frontend && $(PNPM) install

check:
	$(PYTHON) scripts/check_syntax.py
	cd frontend && CI=true CHECK_BUILD=1 $(PNPM) build

login:
	$(PYTHON) automation/wanxiangtai_download.py login

download:
	$(PYTHON) automation/wanxiangtai_download.py download

data:
	$(PYTHON) automation/generate_dashboard_data.py

dev: data
	cd frontend && $(PNPM) dev

build: data
	cd frontend && CI=true $(PNPM) build

package:
	$(PYTHON) automation/deploy_static.py

deploy:
	$(PYTHON) automation/deploy_static.py --commit --push

daily:
	AUTO_DEPLOY=1 $(PYTHON) automation/run_daily.py

preview:
	cd frontend && CI=true $(PNPM) preview

clean:
	$(PYTHON) scripts/clean_project.py
