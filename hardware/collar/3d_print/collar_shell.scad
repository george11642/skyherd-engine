/*
 * SkyHerd Cattle Collar -- Electronics Shell (OpenSCAD)
 *
 * Parametric PETG shell for RAK3172 + MAX-M10S GPS + MPU-6050 + 2500mAh LiPo.
 * IP65 rating achieved via 2mm silicone gasket groove around lid perimeter.
 *
 * Regenerate STL:
 *   openscad collar_shell.scad -o collar_shell.stl
 *   (or: make -C hardware/collar shell)
 *
 * Print settings:
 *   Material:     PETG (UV + moisture resistant; preferred over PLA)
 *   Layer height: 0.2 mm
 *   Walls:        3 perimeters
 *   Infill:       30% gyroid
 *   Supports:     Only for strap slots (tree supports)
 *   Temperature:  240C nozzle / 80C bed
 */

// ---------------------------------------------------------------------------
// Parameters -- adjust to fit your exact PCB stack
// ---------------------------------------------------------------------------

/* [Shell Dimensions] */
shell_length  = 85;   // mm -- long axis (along neck strap direction)
shell_width   = 45;   // mm -- across strap
shell_height  = 22;   // mm -- total external height

wall_t        = 2.5;  // mm -- wall thickness
lid_t         = 2.0;  // mm -- lid thickness
floor_t       = 2.0;  // mm -- floor thickness

/* [Battery Bay] */
bat_l         = 68;   // mm -- battery length
bat_w         = 38;   // mm -- battery width
bat_h         = 9;    // mm -- battery thickness

/* [PCB Stack] */
pcb_l         = 30;   // mm -- RAK3172 module length
pcb_w         = 20;   // mm -- RAK3172 module width
pcb_h         = 5;    // mm -- stack height (module + headers)
pcb_z_offset  = bat_h + 1.5; // above battery bay floor

/* [Antenna Slot] */
ant_slot_w    = 4;    // mm -- IPEX coax width
ant_slot_h    = 3;    // mm -- height of slot in top wall
ant_pos_x     = shell_length / 2 - 8; // position from centre

/* [Gasket Groove] */
gasket_depth  = 2.0;  // mm
gasket_width  = 2.5;  // mm
gasket_offset = 3.0;  // mm from outer edge

/* [Strap Slots] */
strap_w       = 38;   // mm -- 1.5" strap width (imperial)
strap_h       = 5;    // mm -- slot height (fits folded strap)
strap_x_inner = 8;    // mm -- inset from each end

/* [Lid Screw Posts] */
screw_d       = 4.0;  // mm -- M2 screw boss OD
screw_post_h  = 6.0;  // mm
screw_inset   = 5.0;  // mm from corners

/* [USB-C Charging Port] */
usbc_w        = 10.0; // mm -- cutout width
usbc_h        = 4.5;  // mm -- cutout height

// ---------------------------------------------------------------------------
// Derived constants
// ---------------------------------------------------------------------------

inner_l = shell_length - 2 * wall_t;
inner_w = shell_width  - 2 * wall_t;
inner_h = shell_height - floor_t - lid_t;

// ---------------------------------------------------------------------------
// Modules
// ---------------------------------------------------------------------------

module rounded_box(l, w, h, r=3) {
    // Rounded-corner box, centred on XY, z from 0..h
    minkowski() {
        cube([l - 2*r, w - 2*r, h], center=true);
        cylinder(r=r, h=0.01, center=true, $fn=32);
    }
}

module shell_body() {
    difference() {
        // Outer shell
        translate([0, 0, shell_height/2])
            rounded_box(shell_length, shell_width, shell_height, r=4);

        // Inner cavity
        translate([0, 0, floor_t + inner_h/2 + 0.01])
            rounded_box(inner_l, inner_w, inner_h + 0.02, r=3);

        // Lid seat (step for lid to rest on)
        translate([0, 0, shell_height - lid_t - 0.5])
            rounded_box(inner_l - 1, inner_w - 1, lid_t + 1, r=3);

        // Gasket groove in top rim
        translate([0, 0, shell_height - gasket_depth])
            difference() {
                rounded_box(shell_length - 2*gasket_offset,
                            shell_width  - 2*gasket_offset,
                            gasket_depth + 0.1, r=3);
                rounded_box(shell_length - 2*(gasket_offset + gasket_width),
                            shell_width  - 2*(gasket_offset + gasket_width),
                            gasket_depth + 0.2, r=2.5);
            }

        // Antenna slot through top wall (for IPEX coax)
        translate([ant_pos_x, shell_width/2 - wall_t, shell_height - ant_slot_h])
            cube([ant_slot_w, wall_t + 0.2, ant_slot_h + 0.1]);

        // USB-C charging port cutout in front wall
        translate([-usbc_w/2, -shell_width/2 - 0.1, floor_t + 3])
            cube([usbc_w, wall_t + 0.2, usbc_h]);

        // Strap slots -- left end
        translate([-shell_length/2 - 0.1,
                   -strap_w/2,
                   floor_t + inner_h/2 - strap_h/2])
            cube([wall_t + 0.2 + strap_x_inner, strap_w, strap_h]);

        // Strap slots -- right end
        translate([shell_length/2 - strap_x_inner - 0.1,
                   -strap_w/2,
                   floor_t + inner_h/2 - strap_h/2])
            cube([strap_x_inner + wall_t + 0.2, strap_w, strap_h]);
    }
}

module screw_boss(h) {
    // Solid cylindrical boss for M2 screw, hollow top
    difference() {
        cylinder(d=screw_d, h=h, $fn=16);
        translate([0, 0, h - 4])
            cylinder(d=2.2, h=4.1, $fn=12); // M2 pilot hole
    }
}

module screw_bosses() {
    inset = screw_inset;
    x1 =  inner_l/2 - inset;
    x2 = -inner_l/2 + inset;
    y1 =  inner_w/2 - inset;
    y2 = -inner_w/2 + inset;

    for (pos = [[x1,y1], [x1,y2], [x2,y1], [x2,y2]]) {
        translate([pos[0], pos[1], floor_t])
            screw_boss(screw_post_h);
    }
}

module battery_retainer() {
    // Low-profile ledge to keep LiPo from shifting
    translate([-bat_l/2 - 0.5, -bat_w/2, floor_t])
        cube([1.5, bat_w, 2]);
    translate([ bat_l/2 - 1.0, -bat_w/2, floor_t])
        cube([1.5, bat_w, 2]);
}

module pcb_standoffs() {
    // 2mm standoffs for PCB mounting (drill M2 holes in PCB corners)
    so_h = pcb_z_offset;
    for (pos = [[pcb_l/2 - 3, pcb_w/2 - 3],
                [pcb_l/2 - 3, -(pcb_w/2 - 3)],
                [-(pcb_l/2 - 3), pcb_w/2 - 3],
                [-(pcb_l/2 - 3), -(pcb_w/2 - 3)]]) {
        translate([pos[0], pos[1], floor_t])
            cylinder(d=3, h=so_h, $fn=12);
    }
}

// ---------------------------------------------------------------------------
// Main assembly -- body (bottom half)
// ---------------------------------------------------------------------------
module main_body() {
    union() {
        shell_body();
        screw_bosses();
        battery_retainer();
        pcb_standoffs();
    }
}

// ---------------------------------------------------------------------------
// Lid (top half -- print separately, sealed with gasket)
// ---------------------------------------------------------------------------
module lid() {
    translate([0, 0, shell_height + 5]) // offset for preview separation
    difference() {
        rounded_box(shell_length, shell_width, lid_t + 0.5, r=4);

        // M2 screw pass-through holes
        inset = screw_inset;
        x1 =  inner_l/2 - inset;
        x2 = -inner_l/2 + inset;
        y1 =  inner_w/2 - inset;
        y2 = -inner_w/2 + inset;
        for (pos = [[x1,y1], [x1,y2], [x2,y1], [x2,y2]]) {
            translate([pos[0], pos[1], -0.1])
                cylinder(d=2.4, h=lid_t + 0.7, $fn=12);
        }
    }
}

// ---------------------------------------------------------------------------
// Render -- set to "body" or "lid" via command line:
//   openscad -D 'part="lid"' collar_shell.scad -o collar_lid.stl
// ---------------------------------------------------------------------------
part = "body"; // default

if (part == "lid") {
    lid();
} else if (part == "both") {
    main_body();
    lid();
} else {
    main_body();
}
