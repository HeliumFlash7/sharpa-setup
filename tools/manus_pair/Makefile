# Builds manus_pair against the Manus SDK shipped inside sharpa-manus-sdk (vendor/, see scripts/fetch_vendor.sh).
# scripts/setup_teleop.sh runs `make -B` (always relinks, so switching MANUS updates the rpath).
MANUS ?= $(abspath ../../vendor/sharpa-manus-sdk-1.0.1/client/ManusSDK)
# rpath relative to the binary, so the folder can be moved without rebuilding
RPATH := $(shell realpath -m --relative-to="$(CURDIR)" "$(MANUS)/lib")

manus_pair: manus_pair.cpp
	g++ -std=c++17 -O2 -I"$(MANUS)/include" $< -o $@ -L"$(MANUS)/lib" -lManusSDK_Integrated \
	    -Wl,-rpath,'$$ORIGIN/$(RPATH)' -pthread

clean:
	rm -f manus_pair

.PHONY: clean
