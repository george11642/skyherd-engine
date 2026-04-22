# SkyHerd Cattle Collar — Hardware Makefile
#
# Targets:
#   build   — compile firmware for RAK3172
#   flash   — upload via USB-C DFU bootloader
#   test    — run host-side payload unit tests
#   monitor — open serial monitor
#   shell   — regenerate STL from OpenSCAD source
#   clean   — remove PlatformIO build artifacts

FIRMWARE_DIR := firmware
SCAD_SRC     := 3d_print/collar_shell.scad
SCAD_STL     := 3d_print/collar_shell.stl
SCAD_LID_STL := 3d_print/collar_lid.stl

.PHONY: build flash test monitor shell clean help

## Compile firmware for RAK3172 (default environment)
build:
	cd $(FIRMWARE_DIR) && pio run

## Upload firmware via USB-C DFU (hold BOOT, press RESET before running)
flash:
	cd $(FIRMWARE_DIR) && pio run -t upload

## Run host-side payload unit tests (no hardware required)
test:
	cd $(FIRMWARE_DIR) && pio test -e native

## Open serial monitor at 115200 baud
monitor:
	cd $(FIRMWARE_DIR) && pio device monitor

## Regenerate STL from OpenSCAD source
shell:
	openscad $(SCAD_SRC) -o $(SCAD_STL)
	openscad $(SCAD_SRC) -D 'part="lid"' -o $(SCAD_LID_STL)
	@echo "STL files regenerated:"
	@echo "  $(SCAD_STL)"
	@echo "  $(SCAD_LID_STL)"

## Remove PlatformIO build artifacts
clean:
	cd $(FIRMWARE_DIR) && pio run -t clean
	rm -f $(SCAD_STL) $(SCAD_LID_STL)

## Show this help
help:
	@grep -E '^##' $(MAKEFILE_LIST) | sed 's/## //'
