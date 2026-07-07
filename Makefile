# Makefile — 測試入口（spec testing-traceability 元件 2・R1.2/4.2）
# 所有 target 透過 scripts/run-tests.sh，於 Python 3.11 容器內跑 pytest（本地與 CI 同一支）。
.PHONY: test test-unit test-integration test-e2e test-all test-cov trace audit

test: test-unit            ## 預設＝unit 層（CI 主力、可離線）

test-unit:                 ## 只跑 unit（純 mock）
	scripts/run-tests.sh unit

test-integration:          ## 跑 integration（需真實相依；無相依時標示略過）
	scripts/run-tests.sh integration

test-e2e:                  ## 跑 e2e（經 API/SSE，需整服務）
	scripts/run-tests.sh e2e

test-all:                  ## 跑全部層
	scripts/run-tests.sh all

test-cov:                  ## unit + 覆蓋率報告
	scripts/run-tests.sh unit --cov

trace:                     ## 產生追溯矩陣報告
	python3 tools/traceability/scan.py

audit:                     ## 系統不變量稽核（需 DB/容器在線；部署前後必跑，維護準則見腳本頭）
	scripts/audit/check_invariants.sh
