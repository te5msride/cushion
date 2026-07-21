// Cushion manual generator. Run: node build_manual.js
// Output: Cushion_Manual.docx (edit freely in Word afterwards, or edit
// this script and regenerate).
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow,
  TableCell, WidthType, AlignmentType, HeadingLevel, PageBreak,
  ShadingType, BorderStyle,
} = require("docx");

const FIG = path.join(__dirname, "figures");

function pngSize(file) {
  const b = fs.readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}

function img(file, targetW) {
  const p = path.join(FIG, file);
  const { w, h } = pngSize(p);
  return new ImageRun({
    data: fs.readFileSync(p), type: "png",
    transformation: { width: targetW, height: Math.round(h * targetW / w) },
  });
}

const GRAY = "666666";

function p(text, opts = {}) {
  return new Paragraph({
    alignment: opts.center ? AlignmentType.CENTER : AlignmentType.LEFT,
    spacing: { after: opts.after ?? 160 },
    children: [new TextRun({
      text, bold: opts.bold, italics: opts.italic, size: opts.size ?? 22,
      color: opts.color, font: "Helvetica",
    })],
  });
}

function heading(text, level) {
  return new Paragraph({
    heading: level, spacing: { before: 240, after: 200 },
    children: [new TextRun({ text, font: "Helvetica" })],
  });
}

function ioTable(rows, header) {
  const widths = [1500, 1250, 900, 5710];
  const mk = (t, bold, fill) => new TableCell({
    width: { size: widths[0], type: WidthType.DXA },
    shading: fill ? { type: ShadingType.CLEAR, fill } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({ children: [new TextRun({ text: t, bold, size: 18, font: "Helvetica" })] })],
  });
  const row = (cells, bold, fill) => new TableRow({
    children: cells.map((t, i) => new TableCell({
      width: { size: widths[i], type: WidthType.DXA },
      shading: fill ? { type: ShadingType.CLEAR, fill } : undefined,
      margins: { top: 60, bottom: 60, left: 100, right: 100 },
      children: [new Paragraph({ children: [new TextRun({ text: t, bold, size: 18, font: "Helvetica" })] })],
    })),
  });
  return new Table({
    columnWidths: widths,
    width: { size: widths.reduce((a, b) => a + b), type: WidthType.DXA },
    rows: [row(header, true, "EFEFEF"), ...rows.map(r => row(r))],
  });
}

// ---------------------------------------------------------------- data
const components = [
  {
    name: "SofaBody", icon: "SofaBody.png", group: "Define",
    desc: "The deformable finite-element body. Provide a closed solid (Brep preferred) or an existing mesh file; Cushion tet-meshes it via Gmsh and assigns the material properties. All actuation, fixation, monitoring, and display elements attach to a body.",
    inputs: [
      ["geo", "Geometry", "item", "Closed solid. Breps are exported as STEP for exact meshing; meshes as STL."],
      ["volumeFile", "Text", "item", "Alternative to geo: .vtk used as-is (pre-meshed tets); .step/.stl is meshed by Gmsh."],
      ["name", "Text", "item", "Node name, unique per body (default actuator1). SofaResults/SofaShape reference it."],
      ["E", "Number", "item", "Young's modulus, kPa."],
      ["nu", "Number", "item", "Poisson ratio (default 0.4)."],
      ["mass", "Number", "item", "Total mass, kg."],
      ["meshSize", "Number", "item", "Gmsh mesh size factor; smaller = finer tets."],
      ["cavities", "Cavity", "list", "From SofaCavity."],
      ["tendons", "Tendon", "list", "From SofaTendon / SofaTendons."],
      ["regions", "Region", "list", "From SofaRegion."],
      ["fixations", "Box", "list", "Mesh nodes inside each box are clamped to their rest position."],
      ["monitorPts", "Point", "list", "Tracked points, snapped to closest mesh nodes; required for trajectory output."],
      ["collisionGeo", "Geometry", "item", "Collision surface; wire only when contact matters (costs compute)."],
      ["collisionFile", "Text", "item", "Alternative: existing collision .stl path."],
      ["visualGeo", "Geometry", "list", "Display-only surfaces, deformed with the body but never simulated."],
      ["visualFiles", "Text", "list", "Display-only .stl paths, used as-is."],
      ["visualFaces", "Integer", "item", "Decimate visualGeo to this face count on export (0 = off)."],
      ["exportShape", "Integer", "item", "Export the deformed volume mesh every N steps for SofaShape playback (0 = off)."],
    ],
    outputs: [["body", "Body reference, feed into SofaScene."]],
    notes: "",
  },
  {
    name: "SofaCavity", icon: "SofaCavity.png", group: "Define",
    desc: "A pneumatic chamber. The closed surface becomes a SOFA SurfacePressureConstraint driven by the actuation channel; positive pressure inflates, negative deflates.",
    inputs: [
      ["geo", "Geometry", "item", "Closed surface fully inside the body."],
      ["meshFile", "Text", "item", "Alternative: existing closed .stl."],
      ["channel", "Integer", "item", "Actuation channel (column of the schedule) driving this cavity."],
      ["name", "Text", "item", "Default cavity_<channel>."],
    ],
    outputs: [["cavity", "Cavity reference, feed into SofaBody."]],
    notes: "Pressures are commanded in kPa; internal solver scaling is handled automatically.",
  },
  {
    name: "SofaTendon", icon: "SofaTendon.png", group: "Define",
    desc: "A cable/tendon routed through the body (SOFA CableConstraint). Driven in displacement (mm) or force (mN) through its actuation channel.",
    inputs: [
      ["pts", "Point", "list", "Ordered routing points, all inside the body (e.g. Divide Curve). First point = motor side."],
      ["ptsFile", "Text", "item", "Alternative: JSON file of [[x,y,z], ...] points."],
      ["channel", "Integer", "item", "Actuation channel."],
      ["name", "Text", "item", "Default cable_<channel>."],
      ["valueType", "Text", "item", "displacement (mm, default) or force (mN)."],
      ["pullPoint", "Point", "item", "Optional external anchor (motor/pulley) the cable exits toward."],
    ],
    outputs: [["tendon", "Tendon reference, feed into SofaBody."],
              ["pathPts", "Routing points for viewport preview."]],
    notes: "Driving several coupled cables simultaneously: use force mode. Every run also records displacement and force per cable (see SofaResults).",
  },
  {
    name: "SofaTendons", icon: "SofaTendons.png", group: "Define",
    desc: "Multiple tendons from one component. Wire a tree of points (one branch per tendon); channels default to 1..N in branch order.",
    inputs: [
      ["pts", "Point", "tree", "One branch per tendon (an un-flattened Divide Curve over a list of curves)."],
      ["channels", "Integer", "list", "Channel per branch (optional, default 1..N)."],
      ["valueType", "Text", "item", "displacement or force, applied to all tendons."],
      ["pullPoints", "Point", "list", "Optional anchor per tendon, matched by index."],
    ],
    outputs: [["tendons", "List of tendon references, feed into SofaBody (no Merge needed)."],
              ["info", "Summary of created tendons."]],
    notes: "",
  },
  {
    name: "SofaRegion", icon: "SofaRegion.png", group: "Define",
    desc: "A locally stiffened sub-region (membrane, embedded sensor, waveguide). The closed mesh selects body elements and overlays additional stiffness on them; the region is never a separate meshed part.",
    inputs: [
      ["geo", "Geometry", "item", "Closed mesh enclosing the elements to stiffen."],
      ["surface", "Geometry", "item", "Alternative: base surface for the auto-shell mode."],
      ["thickness", "Number", "item", "Shell offset (mm) used with surface: builds a closed hollow shell (a membrane with no inlet, impossible as a Brep)."],
      ["meshFile", "Text", "item", "Alternative: existing closed .stl."],
      ["name", "Text", "item", ""],
      ["E", "Number", "item", "Overlay modulus, kPa, added on top of the body material."],
      ["nu", "Number", "item", "Default 0.4."],
      ["repo", "Text", "item", "Cushion folder path (auto-shell mode only; not needed with the installed plugin)."],
    ],
    outputs: [["region", "Region reference, feed into SofaBody."],
              ["shell", "Generated shell mesh (auto-shell mode preview)."]],
    notes: "",
  },
  {
    name: "SofaTarget", icon: "SofaTarget.png", group: "Define",
    desc: "A rigid interaction object: something to grasp, poke, or rest on. Falls under gravity and responds to contact with any body that has a collision surface.",
    inputs: [
      ["geo", "Geometry", "item", "Closed surface, placed in world coordinates."],
      ["meshFile", "Text", "item", "Alternative: existing closed .stl."],
      ["name", "Text", "item", "Default target1."],
      ["mass", "Number", "item", "kg (default 0.01)."],
    ],
    outputs: [["target", "Target reference, feed into SofaScene."]],
    notes: "Contact requires collisionGeo on the body, and usually a floor (SofaScene.floorZ). Rotational inertia is approximated in this release.",
  },
  {
    name: "PressureProfile", icon: "PressureProfile.png", group: "Actuate",
    desc: "Actuation keyframes for one channel: linear interpolation between (time, value) pairs, resampled into the scene's actuation schedule. Values are kPa for cavities, mm or mN for tendons.",
    inputs: [
      ["channel", "Integer", "item", "Channel this profile drives."],
      ["times", "Number", "list", "Keyframe times, seconds."],
      ["values", "Number", "list", "Keyframe values."],
    ],
    outputs: [["profile", "Profile reference, feed into SofaScene."]],
    notes: "Values hold at the last keyframe: add an explicit return to 0 if the channel should release.",
  },
  {
    name: "SofaProfiles", icon: "SofaProfiles.png", group: "Actuate",
    desc: "Multiple profiles from one component, via trees: one values branch per channel; a single times branch is shared by all.",
    inputs: [
      ["channels", "Integer", "list", "Channel per branch (optional, default 1..N)."],
      ["times", "Number", "tree", "Keyframe times per channel; one branch = shared timeline."],
      ["values", "Number", "tree", "Keyframe values, one branch per channel."],
    ],
    outputs: [["profiles", "List of profile references, feed into SofaScene."],
              ["info", "Summary."]],
    notes: "",
  },
  {
    name: "SofaScene", icon: "SofaScene.png", group: "Simulate",
    desc: "Assembles everything into a runnable SOFA project folder: meshes the bodies, writes the scene description, actuation schedule, and solver configuration. The folder is self-contained and can also be run outside Grasshopper.",
    inputs: [
      ["bodies", "Body", "list", "From SofaBody."],
      ["profiles", "Profile", "list", "From PressureProfile / SofaProfiles."],
      ["targets", "Target", "list", "From SofaTarget (optional)."],
      ["camPos", "Point", "item", "SOFA camera position (optional)."],
      ["camTarget", "Point", "item", "Camera look-at point (optional, needs camPos)."],
      ["viewFile", "Text", "item", "A saved SOFA .view file to use instead (Save View in the SOFA GUI)."],
      ["projDir", "Text", "item", "Output folder, local disk. One folder per design."],
      ["repo", "Text", "item", "Cushion folder path (not needed with the installed plugin)."],
      ["dt", "Number", "item", "Timestep, s (default 0.01)."],
      ["gravityZ", "Number", "item", "mm/s2; default -9810, use 0 while testing."],
      ["floorZ", "Number", "item", "Adds a static floor plane at this height (empty = none)."],
      ["floorSize", "Number", "item", "Floor edge length, mm (default 400)."],
      ["contactRules", "Text", "item", "Advanced contact pairing rules (empty = default friction contact)."],
      ["write", "Boolean", "item", "Toggle True to (re)write the project."],
    ],
    outputs: [["scenePath", "Path to the written scene; feed into SofaRun / SofaResults / SofaShape / SofaPreview."],
              ["info", "What was written; read this first when something is off."]],
    notes: "Units: mm / kPa / kg / s throughout. Rhino document units must be millimeters.",
  },
  {
    name: "SofaRun", icon: "SofaRun.png", group: "Simulate",
    desc: "Launches the SOFA simulation: interactive GUI (press Animate) or headless batch that blocks until finished.",
    inputs: [
      ["scenePath", "Text", "item", "From SofaScene."],
      ["sofaRoot", "Text", "item", "SOFA installation folder (or set the SOFA_ROOT environment variable)."],
      ["repo", "Text", "item", "Cushion folder path (not needed with the installed plugin)."],
      ["gui", "Boolean", "item", "True: SOFA window; False: headless batch."],
      ["winRect", "Integer", "list", "Optional x, y, width, height to place the SOFA window (Windows)."],
      ["run", "Boolean", "item", "Toggle True to launch."],
    ],
    outputs: [["status", "Launch/exit status; the run log is written next to the scene."]],
    notes: "",
  },
  {
    name: "SofaPreview", icon: "SofaPreview.png", group: "Simulate",
    desc: "Rebuilds the written scene as Rhino geometry: the actual simulation tet mesh, cavities, regions, tendon paths, targets, monitor points, and fixation boxes. Wire outputs through Custom Preview components for per-role colors.",
    inputs: [
      ["scenePath", "Text", "item", "From SofaScene."],
      ["repo", "Text", "item", "Cushion folder path (not needed with the installed plugin)."],
      ["refresh", "Boolean", "item", "Toggle to re-read."],
    ],
    outputs: [
      ["volumes", "Simulation mesh surfaces (meshing QA)."],
      ["cavities", "Cavity meshes."], ["regions", "Region meshes."],
      ["targets", "Target meshes."],
      ["tendonCrvs", "Cable routing polylines (pull point included)."],
      ["tendonChs", "Channel number per tendon."],
      ["monitorPts", "Tracked points."], ["fixBoxes", "Fixation boxes."],
      ["info", "Counts and any skipped mesh files."],
    ],
    notes: "",
  },
  {
    name: "SofaResults", icon: "SofaResults.png", group: "Results",
    desc: "Reads simulation results back into Grasshopper: monitored point trajectories, actuation history, and tendon telemetry.",
    inputs: [
      ["scenePath", "Text", "item", "From SofaScene."],
      ["bodyName", "Text", "item", "Body whose monitor to read (SofaBody name)."],
      ["repo", "Text", "item", "Cushion folder path (not needed with the installed plugin)."],
      ["refresh", "Boolean", "item", "Toggle to re-read."],
    ],
    outputs: [
      ["info", "What was found; read this first."],
      ["times", "One time per recorded frame."],
      ["points", "Tree: branch per frame, items = tracked point positions."],
      ["lastPts", "Final frame (quick preview)."],
      ["pTimes", "Actuation sample times."],
      ["pressures", "Tree: branch per channel, commanded/measured values."],
      ["cableNames", "Cable names (when tendons exist)."],
      ["cableDisp", "Tree: displacement per cable, mm."],
      ["cableForce", "Tree: force per cable, mN."],
    ],
    notes: "Typical recipes: points + Tree Branch + slider = scrub the motion; Flip Matrix + Polyline = trajectory curves; pressures + Quick Graph = actuation history.",
  },
  {
    name: "SofaShape", icon: "SofaShape.png", group: "Results",
    desc: "Rebuilds the deformed body surface at any exported frame. Requires exportShape set on SofaBody when the scene was written.",
    inputs: [
      ["scenePath", "Text", "item", "From SofaScene."],
      ["bodyName", "Text", "item", "Body to read."],
      ["frame", "Integer", "item", "Frame index; empty = last. Wire a slider 0..nFrames-1 to scrub."],
      ["repo", "Text", "item", "Cushion folder path (not needed with the installed plugin)."],
      ["refresh", "Boolean", "item", "Toggle to re-read."],
    ],
    outputs: [["mesh", "Deformed surface mesh at the frame."],
              ["nFrames", "Frames available."],
              ["time", "Simulation time of the frame, s."],
              ["info", "Status."]],
    notes: "",
  },
];

const groups = ["Define", "Actuate", "Simulate", "Results"];

// ---------------------------------------------------------------- doc
const children = [];

// --- cover
children.push(new Paragraph({ spacing: { before: 2800 }, children: [] }));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  children: [img("logofinal.png", 340)],
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { before: 400 },
  children: [new TextRun({ text: "CUSHION", size: 72, font: "Helvetica" })],
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { before: 100 },
  children: [new TextRun({ text: "Soft robotics simulation tools for Grasshopper3D", size: 26, font: "Helvetica" })],
}));
children.push(new Paragraph({ children: [new PageBreak()] }));

// --- definition page
children.push(new Paragraph({ spacing: { before: 4200 }, children: [] }));
children.push(p("Cushion", { size: 24 }));
children.push(p("noun", { italic: true, size: 24 }));
children.push(p("A soft pad or pillow, typically placed on a sofa, that makes a rigid structure comfortable to work with.", { size: 24, after: 240 }));
children.push(p("Also: an intermediate layer that softens the interface between two hard things.", { size: 24, after: 400 }));
children.push(p("Cushion is the soft layer between Rhino and SOFA.", { italic: true, size: 24, color: GRAY }));
children.push(new Paragraph({ children: [new PageBreak()] }));

// --- copyright page
children.push(new Paragraph({ spacing: { before: 3600 }, children: [] }));
[
  "CUSHION V0.1 -- Soft robotics simulation tools for Grasshopper3D",
  "",
  "Developed by Trevor Exley and Anderson Brazil Nardin",
  "Soft BioRobotics Perception Lab, Istituto Italiano di Tecnologia",
  "",
  "[website]        [contact email]        [repository URL]",
  "",
  "Licensed under the GNU Lesser General Public License v2.1 or later.",
  "See the LICENSE file in the repository for the full text.",
  "",
  "Cushion interfaces with SOFA (Simulation Open Framework Architecture,",
  "www.sofa-framework.org) and its SoftRobots plugin, which are distributed",
  "under their own licenses and must be installed separately.",
].forEach(t => children.push(new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { after: 60 },
  children: [new TextRun({ text: t, size: 20, font: "Helvetica" })],
})));
children.push(new Paragraph({ children: [new PageBreak()] }));

// --- contents
children.push(heading("Contents", HeadingLevel.HEADING_1));
[
  "1. Abstract",
  "2. Dependencies & Installation",
  "3. Units & Conventions",
  "4. Overview of Tools",
  "5. Component Reference",
].forEach(t => children.push(p(t, { size: 24, after: 80 })));
groups.forEach(g => {
  children.push(p("        " + g, { size: 22, after: 40 }));
  components.filter(c => c.group === g).forEach(c =>
    children.push(p("                " + c.name, { size: 20, after: 30 })));
});
children.push(p("6. Workflow Example: Tendon-Driven Continuum Robot", { size: 24, after: 80 }));
children.push(new Paragraph({ children: [new PageBreak()] }));

// --- abstract
children.push(heading("Abstract", HeadingLevel.HEADING_1));
[
  "Cushion is a plugin for simulating soft robots directly within Rhino and Grasshopper3D. It connects the parametric design environment to SOFA (Simulation Open Framework Architecture) and its SoftRobots plugin: deformable bodies, pneumatic cavities, tendons, stiffened regions, and rigid interaction objects are defined as native Grasshopper components. Cushion meshes the geometry, writes a complete finite-element scene, launches the simulation, and returns trajectories, actuation forces, and deformed shapes to the canvas -- so design iteration and physical simulation live in the same definition.",
  "The workflow grew out of the Monolithic Unit research pipeline (Exley, Nardin, Trunin, Cafiso and Beccai, 2025), in which soft pneumatic actuators designed parametrically in Grasshopper were simulated in SOFA for actuation and sensor-placement studies. Cushion generalizes that pipeline: any closed solid can become a simulated soft body, with materials, actuation, and boundary conditions assigned per component, and results flowing back for downstream design logic -- workspace analysis, grasp evaluation, or optimization loops.",
  "V0.1 -- Initial release. Pneumatic and tendon actuation, local stiffening regions, rigid targets and contact, scene preview, trajectory monitoring, tendon telemetry, and deformed-shape playback. Requires the freely available SOFA binaries (v24.06).",
].forEach(t => children.push(p(t, { size: 22, after: 240 })));
children.push(new Paragraph({ children: [new PageBreak()] }));

// --- dependencies
children.push(heading("Dependencies & Installation", HeadingLevel.HEADING_1));
[
  "Rhino 8 with Grasshopper.",
  "SOFA v24.06 binaries with the SofaPython3, SoftRobots, STLIB and SofaValidation plugins (all included in the official release bundle from www.sofa-framework.org/download). Set the SOFA_ROOT environment variable to the installation folder, or wire the path into SofaRun.",
  "Python 3.10 with numpy, for SOFA's embedded interpreter (see the installation guide for per-platform steps; this is the most common setup issue).",
  "Gmsh (Python package) is installed automatically into Rhino's Python on first use; the first scene write needs an internet connection and about a minute.",
].forEach(t => children.push(new Paragraph({
  spacing: { after: 140 },
  children: [new TextRun({ text: "-  " + t, size: 22, font: "Helvetica" })],
})));
children.push(heading("Installing Cushion", HeadingLevel.HEADING_2));
[
  "From the Rhino Package Manager: run the _PackageManager command, search for Cushion, install, restart Rhino. The Cushion tab appears in Grasshopper.",
  "Or manually from food4Rhino: download the .gha file, then in Grasshopper open File > Special Folders > Components Folder, copy the .gha there. On Windows, right-click the downloaded file > Properties > Unblock before copying. Restart Rhino.",
].forEach(t => children.push(new Paragraph({
  spacing: { after: 140 },
  children: [new TextRun({ text: "-  " + t, size: 22, font: "Helvetica" })],
})));
children.push(heading("Links", HeadingLevel.HEADING_2));
[
  "Rhino 8: www.rhino3d.com",
  "SOFA v24.06 binaries: www.sofa-framework.org/download",
  "Python 3.10 (python.org installer): www.python.org/downloads/release/python-31011",
  "Cushion repository & issues: [repository URL]",
  "Manual, examples, install guides: [repository URL]/docs",
].forEach(t => children.push(new Paragraph({
  spacing: { after: 100 },
  children: [new TextRun({ text: "-  " + t, size: 22, font: "Helvetica" })],
})));
children.push(p("Verify the SOFA side before using Cushion:", { size: 22, after: 80 }));
children.push(p("<SOFA>/bin/runSofa -l SofaPython3 -g batch -n 1", { size: 20, after: 240 }));
children.push(heading("Units & Conventions", HeadingLevel.HEADING_1));
[
  "Millimeters, kilopascals, kilograms, seconds. Gravity -9810 mm/s2 in world Z. Geometry passes from Rhino to SOFA 1:1 -- no transform, no unit conversion. The Rhino document must be in millimeters.",
].forEach(t => children.push(p(t, { size: 22, after: 200 })));
children.push(new Paragraph({ children: [new PageBreak()] }));

// --- overview of tools
children.push(heading("Overview of Tools", HeadingLevel.HEADING_1));
children.push(p("[toolbar screenshot placeholder -- replace with a capture of the Cushion tab]", { italic: true, color: GRAY, after: 300 }));
groups.forEach(g => {
  children.push(heading(g, HeadingLevel.HEADING_2));
  components.filter(c => c.group === g).forEach(c => {
    children.push(new Paragraph({
      spacing: { after: 120 },
      children: [
        img(c.icon, 42),
        new TextRun({ text: "   " + c.name + " -- ", bold: true, size: 22, font: "Helvetica" }),
        new TextRun({ text: c.desc.split(".")[0] + ".", size: 22, font: "Helvetica" }),
      ],
    }));
  });
});
children.push(new Paragraph({ children: [new PageBreak()] }));

// --- component pages
children.push(heading("Component Reference", HeadingLevel.HEADING_1));
components.forEach((c, i) => {
  children.push(new Paragraph({
    spacing: { before: 200, after: 100 },
    children: [img(c.icon, 64), new TextRun({ text: "   " + c.name, bold: true, size: 40, font: "Helvetica" })],
  }));
  children.push(p(c.group, { color: GRAY, size: 20, after: 160 }));
  children.push(p(c.desc, { size: 22, after: 240 }));
  children.push(p("Inputs", { bold: true, size: 24, after: 100 }));
  children.push(ioTable(c.inputs, ["Name", "Type", "Access", "Description"]));
  children.push(p("", { after: 100 }));
  children.push(p("Outputs", { bold: true, size: 24, after: 100 }));
  children.push(ioTable(c.outputs.map(o => [o[0], "", "", o[1]]), ["Name", "", "", "Description"]));
  if (c.notes) {
    children.push(p("", { after: 100 }));
    children.push(p("Notes: " + c.notes, { italic: true, size: 20 }));
  }
  if (i < components.length - 1) children.push(new Paragraph({ children: [new PageBreak()] }));
});
children.push(new Paragraph({ children: [new PageBreak()] }));

// --- example
children.push(heading("Workflow Example: Tendon-Driven Continuum Robot", HeadingLevel.HEADING_1));
[
  "A cylindrical continuum robot with three tendons at 120 degrees, built entirely from native Grasshopper geometry, actuated with a rotating pull direction, and post-processed into a workspace boundary.",
  "1. Body: Circle (r 12) > Extrude (z 100) > Cap Holes > SofaBody (E 100 kPa, mass 0.03 kg).",
  "2. Tendons: three lines at radius 8, Divide Curve > SofaTendons (tree input), valueType force.",
  "3. Fixation: box around the base; monitor points along the axis.",
  "4. Profiles: 13 keyframes per channel sweeping Tmax * max(0, cos(30 deg * k - phi)) -- the resultant pull direction rotates 360 degrees.",
  "5. SofaScene (gravity 0) > SofaPreview to verify > SofaRun.",
  "6. SofaResults: tip positions per frame > convex hull = workspace bounds; cableForce/cableDisp confirm the commanded lobes.",
  "[screenshot placeholders: canvas, SOFA window, workspace hull]",
].forEach(t => children.push(p(t, { size: 22, after: 160 })));

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Helvetica" } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 36, bold: true, color: "2D2D2D", font: "Helvetica" } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, color: "F05423", font: "Helvetica" } },
    ],
  },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 },
                          margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
    children,
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(path.join(__dirname, "Cushion_Manual.docx"), buf);
  console.log("wrote Cushion_Manual.docx");
});
