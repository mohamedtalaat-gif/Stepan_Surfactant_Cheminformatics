# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# PyMOL script for the five aggregate models in this folder (geometric models; not molecular dynamics).
#   cd docs/card/models
#   pymol stepan_lab.pml
# Show another model with:  disable all  then  enable aos_betaine_rod
bg_color white
load sls_sphere.pdb
load sls_rod.pdb
load aos_betaine_sphere.pdb
load aos_betaine_rod.pdb
load ester_quat_bilayer.pdb
hide everything
show spheres
set sphere_scale, 0.6
set_color c_sls, [0.208, 0.816, 0.725]
set_color c_aos, [1.000, 0.478, 0.565]
set_color c_eq, [0.357, 0.616, 1.000]
set_color c_cet, [0.706, 0.549, 1.000]
set_color c_head, [1.000, 0.784, 0.239]
color c_sls, resn SLS and elem C
color c_aos, resn AOS and elem C
color c_sls, resn COC and elem C
color c_eq, resn EQ_ and elem C
color c_cet, resn CET and elem C
color c_head, not elem C
set ray_shadows, 1
set depth_cue, 1
disable all
enable aos_betaine_sphere
zoom
# The B-factor column marks the carbon atoms that come from renewable sources (1.0) or not (0.0):
# color grey60, elem C
# color green, elem C and b > 0.5
