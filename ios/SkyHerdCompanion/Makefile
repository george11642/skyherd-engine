# SkyHerdCompanion iOS — Makefile
# ─────────────────────────────────────────────────────────────────────────────
# Targets:
#   bootstrap   Generate Xcode project via XcodeGen
#   build       Debug build for generic iOS device
#   test        Run unit tests on iOS Simulator (iPhone 15)
#   install     Deploy to connected device via ios-deploy
#   clean       Remove build artefacts

SCHEME    = SkyHerdCompanion
PROJECT   = SkyHerdCompanion.xcodeproj
SIM_DEST  = platform=iOS Simulator,name=iPhone 15
DEVICE    = generic/platform=iOS
BUILD_DIR = build

.PHONY: bootstrap build test install clean

bootstrap:
	./bootstrap.sh

build: $(PROJECT)
	xcodebuild \
	  -project $(PROJECT) \
	  -scheme $(SCHEME) \
	  -destination '$(DEVICE)' \
	  -configuration Debug \
	  -derivedDataPath $(BUILD_DIR) \
	  build

test: $(PROJECT)
	xcodebuild test \
	  -project $(PROJECT) \
	  -scheme $(SCHEME) \
	  -destination '$(SIM_DEST)' \
	  -derivedDataPath $(BUILD_DIR) \
	  -enableCodeCoverage YES

install: $(PROJECT)
	@if command -v ios-deploy &>/dev/null; then \
	  APP=$$(find $(BUILD_DIR) -name "$(SCHEME).app" | head -1); \
	  if [ -z "$$APP" ]; then echo "Run 'make build' first"; exit 1; fi; \
	  ios-deploy --bundle "$$APP" --debug; \
	else \
	  echo "ios-deploy not found. Install with: brew install ios-deploy"; \
	  echo "Alternatively, open $(PROJECT) in Xcode and press ⌘R."; \
	  echo "For TestFlight distribution, see docs/HARDWARE_MAVIC_IOS.md."; \
	fi

clean:
	rm -rf $(BUILD_DIR)
	xcodebuild clean -project $(PROJECT) -scheme $(SCHEME) 2>/dev/null || true

$(PROJECT):
	@echo "$(PROJECT) not found — running bootstrap..."
	$(MAKE) bootstrap
