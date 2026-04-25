import SwiftUI

struct MapView: View {
    @Environment(AppState.self) private var appState
    @State private var selectedEntity: SelectedEntity? = nil

    // Zoom + pan state
    @State private var scale: CGFloat = 1.0
    @State private var offset: CGSize = .zero
    @State private var lastScale: CGFloat = 1.0
    @State private var lastOffset: CGSize = .zero

    private var vm: MapViewModel { appState.mapVM }

    var body: some View {
        NavigationStack {
            GeometryReader { geo in
                ZStack {
                    Color.skhBg0.ignoresSafeArea()

                    if let snapshot = vm.snapshot {
                        // Ranch canvas with gesture support
                        ranchCanvas(snapshot: snapshot, size: geo.size)
                            .gesture(zoomGesture)
                            .gesture(panGesture)
                    } else {
                        waitingState
                    }

                    // Top-left: connection badge
                    VStack {
                        HStack {
                            ConnectionBadge(state: appState.connectionState)
                                .padding(SkyHerdSpacing.sm)
                            Spacer()
                            // Layer controls (top-right)
                            layerControls
                                .padding(SkyHerdSpacing.sm)
                        }
                        Spacer()
                        HStack(alignment: .bottom) {
                            // Legend
                            mapLegend
                                .padding(SkyHerdSpacing.sm)
                            Spacer()
                            // Active scenario indicator
                            if let name = vm.activeScenario {
                                activeScenarioBadge(name: name)
                                    .padding(SkyHerdSpacing.sm)
                            }
                        }
                    }
                }
            }
            .navigationTitle("Ranch Map")
            .navigationBarTitleDisplayMode(.inline)
            .sheet(item: $selectedEntity) { entity in
                EntityInspectSheet(entity: entity)
                    .presentationDetents([.medium])
            }
        }
        .onAppear { vm.onAppear() }
        .onDisappear { vm.onDisappear() }
    }

    // MARK: - Ranch Canvas

    private func ranchCanvas(snapshot: WorldSnapshot, size: CGSize) -> some View {
        let canvasSize = min(size.width, size.height) * 0.95
        return Canvas { ctx, sz in
            let s = sz.width  // canvas is square

            // 1. Background terrain
            ctx.fill(
                Path(CGRect(origin: .zero, size: sz)),
                with: .color(Color(red: 0.13, green: 0.16, blue: 0.11))
            )

            // 2. Paddock fills
            if vm.showPaddocks {
                for paddock in snapshot.paddocks {
                    drawPaddock(ctx: ctx, paddock: paddock, s: s, activeScenario: vm.activeScenario)
                }
            }

            // 3. Paddock labels
            if vm.showPaddocks {
                for paddock in snapshot.paddocks {
                    drawPaddockLabel(ctx: ctx, paddock: paddock, s: s)
                }
            }

            // 4. Fence boundary
            if vm.showFences {
                drawFenceBoundary(ctx: ctx, s: s)
                // Breach pins
                for breach in vm.breachPins {
                    drawBreachPin(ctx: ctx, breach: breach, s: s)
                }
            }

            // 5. Water tanks
            if vm.showTanks {
                for tank in snapshot.waterTanks {
                    drawTank(ctx: ctx, tank: tank, s: s)
                }
            }

            // 6. Cows
            if vm.showCows {
                for cow in snapshot.cows {
                    drawCow(ctx: ctx, cow: cow, s: s)
                }
            }

            // 7. Predators
            if vm.showPredators {
                for predator in snapshot.predators {
                    drawPredator(ctx: ctx, predator: predator, s: s)
                }
            }

            // 8. Drone
            if vm.showDrone {
                drawDrone(ctx: ctx, drone: snapshot.drone, s: s)
            }

        }
        .frame(width: canvasSize, height: canvasSize)
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .strokeBorder(Color.skhLine, lineWidth: 1)
        )
        .scaleEffect(scale)
        .offset(offset)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        // Tap detection overlay for entity inspection
        .overlay(
            tappableEntityOverlay(snapshot: snapshot, canvasSize: canvasSize)
        )
    }

    // MARK: - Canvas drawing primitives

    private func drawPaddock(ctx: GraphicsContext, paddock: Paddock, s: CGFloat, activeScenario: String?) {
        guard paddock.bounds.count >= 4 else { return }
        let minX = paddock.bounds[0] * s
        let minY = paddock.bounds[1] * s
        let maxX = paddock.bounds[2] * s
        let maxY = paddock.bounds[3] * s
        let rect = CGRect(x: minX, y: minY, width: maxX - minX, height: maxY - minY)
        let path = Path(rect)

        // Color by forage %
        let forage = paddock.foragePct
        let fillColor: Color
        if forage > 0.6 {
            fillColor = Color.skhSage.opacity(0.25)
        } else if forage > 0.3 {
            fillColor = Color.skhWarn.opacity(0.2)
        } else {
            fillColor = Color.skhDanger.opacity(0.15)
        }

        ctx.fill(path, with: .color(fillColor))

        // Glow tint for active scenario paddock
        if activeScenario != nil {
            ctx.fill(path, with: .color(Color.skhWarn.opacity(0.06)))
        }

        ctx.stroke(path, with: .color(Color.skhLine.opacity(0.6)), lineWidth: 1)
    }

    private func drawPaddockLabel(ctx: GraphicsContext, paddock: Paddock, s: CGFloat) {
        guard paddock.bounds.count >= 4 else { return }
        let cx = ((paddock.bounds[0] + paddock.bounds[2]) / 2) * s
        let cy = ((paddock.bounds[1] + paddock.bounds[3]) / 2) * s
        let text = Text(paddock.id)
            .font(.system(size: 10, weight: .medium, design: .rounded))
            .foregroundStyle(Color.skhText2)
        ctx.draw(text, at: CGPoint(x: cx, y: cy))
    }

    private func drawFenceBoundary(ctx: GraphicsContext, s: CGFloat) {
        let rect = CGRect(x: 1, y: 1, width: s - 2, height: s - 2)
        ctx.stroke(Path(rect), with: .color(Color.skhLine), lineWidth: 2)
    }

    private func drawBreachPin(ctx: GraphicsContext, breach: NeighborAlertEvent, s: CGFloat) {
        // Place at edge of canvas
        let x: CGFloat = s * 0.95
        let y: CGFloat = s * 0.05
        let pinRect = CGRect(x: x - 8, y: y - 8, width: 16, height: 16)
        ctx.fill(Path(ellipseIn: pinRect), with: .color(Color.skhDanger))
        let sym = Text("!")
            .font(.system(size: 10, weight: .bold))
            .foregroundStyle(Color.white)
        ctx.draw(sym, at: CGPoint(x: x, y: y))
    }

    private func drawTank(ctx: GraphicsContext, tank: WaterTank, s: CGFloat) {
        guard tank.pos.count >= 2 else { return }
        let x = tank.pos[0] * s
        let y = tank.pos[1] * s
        let r: CGFloat = 10
        let outerRect = CGRect(x: x - r, y: y - r, width: r * 2, height: r * 2)

        // Outer ring
        ctx.stroke(Path(ellipseIn: outerRect), with: .color(Color.skhSky.opacity(0.6)), lineWidth: 2)

        // Fill level arc (simulate as inner filled circle with opacity by level)
        let fillAlpha = min(1.0, max(0.1, tank.levelPct))
        let innerR = r * 0.7 * fillAlpha
        let innerRect = CGRect(x: x - innerR, y: y - innerR, width: innerR * 2, height: innerR * 2)
        ctx.fill(Path(ellipseIn: innerRect), with: .color(Color.skhSky.opacity(0.5)))

        // Label
        let pct = Int(tank.levelPct * 100)
        let label = Text("\(pct)%").font(.system(size: 8, weight: .medium)).foregroundStyle(Color.skhSky)
        ctx.draw(label, at: CGPoint(x: x, y: y + r + 7))
    }

    private func drawCow(ctx: GraphicsContext, cow: Cow, s: CGFloat) {
        guard cow.pos.count >= 2 else { return }
        let x = cow.pos[0] * s
        let y = cow.pos[1] * s
        let r: CGFloat = 5
        let rect = CGRect(x: x - r, y: y - r, width: r * 2, height: r * 2)
        let color = Color.cowColor(for: cow.state)
        ctx.fill(Path(ellipseIn: rect), with: .color(color.opacity(0.9)))
        // Sick/calving ring
        if cow.state == "sick" || cow.state == "labor" || cow.state == "calving" {
            let ringRect = rect.insetBy(dx: -2, dy: -2)
            ctx.stroke(Path(ellipseIn: ringRect), with: .color(color), lineWidth: 1.5)
        }
    }

    private func drawPredator(ctx: GraphicsContext, predator: Predator, s: CGFloat) {
        guard predator.pos.count >= 2 else { return }
        let x = predator.pos[0] * s
        let y = predator.pos[1] * s
        let r: CGFloat = 7
        // X mark
        var path = Path()
        path.move(to: CGPoint(x: x - r, y: y - r))
        path.addLine(to: CGPoint(x: x + r, y: y + r))
        path.move(to: CGPoint(x: x + r, y: y - r))
        path.addLine(to: CGPoint(x: x - r, y: y + r))
        ctx.stroke(path, with: .color(Color.skhDanger), lineWidth: 2.5)
        // Threat ring for high
        if predator.threatLevel == "high" {
            let ringRect = CGRect(x: x - r - 4, y: y - r - 4, width: (r + 4) * 2, height: (r + 4) * 2)
            ctx.stroke(Path(ellipseIn: ringRect), with: .color(Color.skhDanger.opacity(0.5)), lineWidth: 1)
        }
    }

    private func drawDrone(ctx: GraphicsContext, drone: Drone, s: CGFloat) {
        // Drone position: use center of canvas if lat/lon only (normalized not available)
        // In mock mode, drone has lat/lon but no normalized pos — place at center
        let x: CGFloat = s * 0.5
        let y: CGFloat = s * 0.5
        let r: CGFloat = 8

        // Triangle pointing up
        var path = Path()
        path.move(to: CGPoint(x: x, y: y - r))
        path.addLine(to: CGPoint(x: x + r * 0.7, y: y + r * 0.5))
        path.addLine(to: CGPoint(x: x - r * 0.7, y: y + r * 0.5))
        path.closeSubpath()

        let isActive = drone.state == "patrol" || drone.state == "investigating"
        let droneColor = Color.skhSky
        ctx.fill(path, with: .color(droneColor.opacity(isActive ? 0.9 : 0.5)))

        // Battery indicator
        if let bat = drone.batteryPct {
            let batColor: Color = bat > 0.5 ? .skhOk : bat > 0.2 ? .skhWarn : .skhDanger
            let label = Text(String(format: "%.0f%%", bat))
                .font(.system(size: 8, weight: .medium))
                .foregroundStyle(batColor)
            ctx.draw(label, at: CGPoint(x: x, y: y + r + 8))
        }
    }

    // MARK: - Tappable overlay for entity inspection

    private func tappableEntityOverlay(snapshot: WorldSnapshot, canvasSize: CGFloat) -> some View {
        GeometryReader { geo in
            let s = canvasSize
            let originX = (geo.size.width - canvasSize) / 2
            let originY = (geo.size.height - canvasSize) / 2

            ZStack {
                // Transparent tap areas for cows
                if vm.showCows {
                    ForEach(snapshot.cows) { cow in
                        if cow.pos.count >= 2 {
                            let cx = originX + cow.pos[0] * s * scale + offset.width
                            let cy = originY + cow.pos[1] * s * scale + offset.height
                            Circle()
                                .fill(Color.clear)
                                .frame(width: 24, height: 24)
                                .contentShape(Circle())
                                .position(x: cx, y: cy)
                                .onTapGesture { selectedEntity = .cow(cow) }
                        }
                    }
                }

                // Predators
                if vm.showPredators {
                    ForEach(snapshot.predators) { predator in
                        if predator.pos.count >= 2 {
                            let px = originX + predator.pos[0] * s * scale + offset.width
                            let py = originY + predator.pos[1] * s * scale + offset.height
                            Circle()
                                .fill(Color.clear)
                                .frame(width: 28, height: 28)
                                .contentShape(Circle())
                                .position(x: px, y: py)
                                .onTapGesture { selectedEntity = .predator(predator) }
                        }
                    }
                }

                // Tanks
                if vm.showTanks {
                    ForEach(snapshot.waterTanks) { tank in
                        if tank.pos.count >= 2 {
                            let tx = originX + tank.pos[0] * s * scale + offset.width
                            let ty = originY + tank.pos[1] * s * scale + offset.height
                            Circle()
                                .fill(Color.clear)
                                .frame(width: 28, height: 28)
                                .contentShape(Circle())
                                .position(x: tx, y: ty)
                                .onTapGesture { selectedEntity = .tank(tank) }
                        }
                    }
                }

                // Drone tap area (center)
                if vm.showDrone {
                    let dx = originX + s * 0.5 * scale + offset.width
                    let dy = originY + s * 0.5 * scale + offset.height
                    Circle()
                        .fill(Color.clear)
                        .frame(width: 32, height: 32)
                        .contentShape(Circle())
                        .position(x: dx, y: dy)
                        .onTapGesture { selectedEntity = .drone(snapshot.drone) }
                }
            }
        }
    }

    // MARK: - Layer controls panel

    private var layerControls: some View {
        VStack(alignment: .trailing, spacing: 4) {
            layerToggle(icon: "square.split.2x2.fill", label: "Paddocks",
                        isOn: vm.showPaddocks) { vm.showPaddocks.toggle() }
            layerToggle(icon: "minus", label: "Fences",
                        isOn: vm.showFences) { vm.showFences.toggle() }
            layerToggle(icon: "circle.fill", label: "Cows",
                        isOn: vm.showCows) { vm.showCows.toggle() }
            layerToggle(icon: "triangle.fill", label: "Drone",
                        isOn: vm.showDrone) { vm.showDrone.toggle() }
            layerToggle(icon: "xmark", label: "Predators",
                        isOn: vm.showPredators) { vm.showPredators.toggle() }
            layerToggle(icon: "drop.fill", label: "Tanks",
                        isOn: vm.showTanks) { vm.showTanks.toggle() }
        }
        .padding(SkyHerdSpacing.sm)
        .background(Color.skhBg1.opacity(0.9), in: RoundedRectangle(cornerRadius: 8))
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .strokeBorder(Color.skhLine, lineWidth: 1)
        )
    }

    @ViewBuilder
    private func layerToggle(icon: String, label: String, isOn: Bool, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack(spacing: 4) {
                Image(systemName: icon)
                    .font(.system(size: 9))
                    .frame(width: 12)
                Text(label)
                    .font(SkyHerdTypography.caption2)
            }
            .foregroundStyle(isOn ? Color.skhText1 : Color.skhText2.opacity(0.4))
        }
        .buttonStyle(.plain)
        .accessibilityLabel("\(label): \(isOn ? "visible" : "hidden")")
    }

    // MARK: - Legend

    private var mapLegend: some View {
        VStack(alignment: .leading, spacing: 4) {
            legendItem(color: .skhCowHealthy, label: "Healthy cow")
            legendItem(color: .skhCowSick, label: "Sick cow")
            legendItem(color: .skhSky, label: "Drone")
            legendItem(color: .skhDanger, label: "Predator")
            legendItem(color: .skhSky.opacity(0.5), label: "Water tank")
        }
        .padding(SkyHerdSpacing.sm)
        .background(Color.skhBg1.opacity(0.9), in: RoundedRectangle(cornerRadius: 8))
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .strokeBorder(Color.skhLine, lineWidth: 1)
        )
    }

    private func legendItem(color: Color, label: String) -> some View {
        HStack(spacing: 6) {
            Circle().fill(color).frame(width: 8, height: 8)
            Text(label)
                .font(SkyHerdTypography.caption2)
                .foregroundStyle(Color.skhText2)
        }
    }

    private func activeScenarioBadge(name: String) -> some View {
        HStack(spacing: 4) {
            Circle().fill(Color.skhWarn).frame(width: 6, height: 6)
            Text(name.replacingOccurrences(of: "_", with: " ").capitalized)
                .font(SkyHerdTypography.caption2)
                .foregroundStyle(Color.skhWarn)
        }
        .padding(.horizontal, SkyHerdSpacing.sm)
        .padding(.vertical, 4)
        .background(Color.skhWarn.opacity(0.12), in: Capsule())
    }

    // MARK: - Waiting state

    private var waitingState: some View {
        VStack(spacing: SkyHerdSpacing.md) {
            Image(systemName: "map")
                .font(.system(size: 48))
                .foregroundStyle(Color.skhText2)
            Text("Waiting for sim data…")
                .font(SkyHerdTypography.heading)
                .foregroundStyle(Color.skhText2)
            Text("Start the backend with `make dashboard`")
                .font(SkyHerdTypography.caption)
                .foregroundStyle(Color.skhText2)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Gestures

    private var zoomGesture: some Gesture {
        MagnificationGesture()
            .onChanged { value in
                scale = max(0.5, min(5.0, lastScale * value))
            }
            .onEnded { value in
                lastScale = scale
            }
    }

    private var panGesture: some Gesture {
        DragGesture()
            .onChanged { value in
                offset = CGSize(
                    width: lastOffset.width + value.translation.width,
                    height: lastOffset.height + value.translation.height
                )
            }
            .onEnded { _ in
                lastOffset = offset
            }
    }
}

// MARK: - Entity Inspect Sheet

struct EntityInspectSheet: View {
    let entity: SelectedEntity

    var body: some View {
        VStack(alignment: .leading, spacing: SkyHerdSpacing.md) {
            HStack {
                Text(entity.title)
                    .font(SkyHerdTypography.heading)
                    .foregroundStyle(Color.skhText0)
                Spacer()
                Image(systemName: entityIcon)
                    .foregroundStyle(entityColor)
            }
            .padding(.horizontal, SkyHerdSpacing.md)
            .padding(.top, SkyHerdSpacing.md)

            Divider().overlay(Color.skhLine)

            ForEach(entity.statusLines, id: \.self) { line in
                Text(line)
                    .font(SkyHerdTypography.body)
                    .foregroundStyle(Color.skhText1)
                    .padding(.horizontal, SkyHerdSpacing.md)
            }

            Spacer()
        }
        .background(Color.skhBg1)
        .presentationBackground(Color.skhBg1)
    }

    private var entityIcon: String {
        switch entity {
        case .cow:      return "circle.fill"
        case .drone:    return "triangle.fill"
        case .predator: return "xmark.circle.fill"
        case .tank:     return "drop.fill"
        }
    }

    private var entityColor: Color {
        switch entity {
        case .cow(let c): return Color.cowColor(for: c.state)
        case .drone:      return .skhSky
        case .predator:   return .skhDanger
        case .tank:       return .skhSky
        }
    }
}

