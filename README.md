# ModuleModo

Procedural low-poly wall modules for Blender 5.2+.

![preview](preview.png)

**Add > Mesh > Wall Module**, or the **ModuleModo** tab in the 3D viewport sidebar, where the 44 buttons are grouped into collapsible sections (Windows, Doors and Entrance, Corners, Bay Windows, Balcony and Loggia, Other) and related variants share a row. All parameters live in the redo panel, so they can be tweaked right after creation.

The module is built the way you would model it by hand: **plane, inset, extrude**.

- One plane at Y=0 facing +Y (default 3 x 3 m), no thickness and no back side
- The opening is inset into four faces with diagonals from the wall corners to the opening corners, then its inner fill (quads and one triangle) is pushed back by `Depth` towards -Y
- Opening: window, door (open at the floor) or solid plane; size, offset, height from floor
- Corner module: two window walls meeting at an outer corner, with the plinth and cornice wrapping around it (windows on both walls or on one)
- Inner corner module: the matching inner corner, bands mitred along one diagonal
- Bay window (oriel), splayed or box, with windows only; a full-height variant with no top or bottom stacks into floors (plinth on the ground floor, cornice on the top one)
- Plinth (bottom band) and cornice (top band) for any module: full-width rectangles extruded out of the wall (the plinth keeps its bottom face), open at the sides so neighbouring modules continue them
- Door with a threshold; entrance module: 1-3 doors on a threshold with a porch slab (no bottom face, it stands on the ground) and an optional canopy slab
- Raised entrance with stairs: a 4 m module with a landing 1 m above the ground and steps up from the ground (adjustable rise, step count and tread depth); its side edges match neighbouring 4 m modules
- Loggia module: a recess in the facade (three extrudes) with a parapet in front, with a door and a window or a single door on its back wall
- Balcony module: door and window side by side with tops aligned, optional balcony slab under them (a thick, long sill)
- 1 to 3 openings, side by side or stacked (windows); the wall is cut into one cell per opening, each cell gets its own inset and extrude
- Arched top: round or pointed (gothic) arch, arch rise and segment count; the wall above the arch is a fan from the two top corners
- Underground module (3 x 0.5 m, built below level 0, pivot at Z=0) and attic / technical floor (3 x 1 m, with an optional small square window and cornice) for stacking whole buildings
- Shutters as separate objects (children of the module, origin on the hinge axis) for straight, round and pointed windows
- Pediment (a gable over a straight top), keystone at the top of an arch band, a panel under the window, a belt course with a plain strip above it, and pilasters at the ends of the module
- Window frame: two posts and a head round the window (an arch band over an arch), extruded out of the wall; without a sill it is a closed ring (a П for a door), with a sill the frame stands on it as a separate body
- Window trim: a trapezoid lintel over a straight top and an arch band round round or pointed arches, extruded out of the wall
- Window sill (optional, or use the "Window Wall (No Sill)" button): the plane rectangle under the window extruded out towards +Y (thickness, depth)
- Pivot at the bottom center or the bottom-left corner
- Smooth by Angle (default 30 degrees): flat faces stay flat, steps along an arch get smooth shading, 90 degree corners stay hard; no modifier
- Auto UV right after modeling: cube projection and Pack Islands without rotation, margin 0.01 (the same recipe as Auto UV in TechArt Tools)

![topology](topology.png)

Build the installable zip with `build.ps1`.

## License

Free and open source under the [GNU GPL v3 or later](LICENSE) (the same family of licenses as Blender itself). You can use the modules you generate in any project, commercial ones included.
