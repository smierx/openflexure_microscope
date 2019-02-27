#!python
from __future__ import print_function
import re
import argparse
import functools

"""This script generates the Makefile for the Openflexure Microscope.

It is intended to be run whenever you need a new makefile.  The makefile lives in
the repository and is versioned, so most people never need to run this script.
"""

body_versions = ["LS65", "LS65-M", "LS75", "LS75-M"]

cameras = ["picamera_2", "logitech_c270", "m12"]
lenses = ["pilens", "c270_lens", "m12_lens", "rms_f40d16", "rms_f50d13"]
optics_versions_LS65 = ["picamera_2_pilens", "logitech_c270_c270_lens"]
optics_versions_LS65 += [cam + "_" + lens for cam in cameras for lens in lenses if "rms" in lens] + ["m12_m12_lens"]
optics_versions = [v + "_LS65" for v in optics_versions_LS65]
sample_riser_versions = ['LS10']
slide_riser_versions = ['LS10']
stand_versions = ['LS65-30', 'LS65-160']

def body_parameters(version):
    """Retrieve the parameters we pass to OpenSCAD to generate the given body version."""
    p = {"motor_lugs": False, "sample_z":-1, "big_stage":None}
    matching_version = ""
    for v in body_versions: # first, pick the longest matching version string.
        if v in version and len(v) > len(matching_version):
            matching_version = v
    m = re.match("(LS|SS)([\d]{2})((-M){0,1})", matching_version)
    p["big_stage"] = m.group(1)=="LS"
    p["motor_lugs"] = m.group(4)=="-M"
    p["sample_z"] = m.group(2)
    return p
    
def optics_module_parameters(version):
    """Figure out the parameters we need to generate the optics module"""
    m = re.search("({cam})_({lens})_({body})".format(
                            cam="|".join(cameras), 
                            lens="|".join(lenses),
                            body="|".join(body_versions)), 
                        version)
    if m is None:
        raise ValueError("Error finding optics module parameters from version string '{}'".format(version))
    p = {"camera": m.group(1), "optics": m.group(2)}
    p.update(body_parameters(m.group(3)))
    return p
	
def stand_parameters(version):
	m = re.match("({body})-([\d]+)$".format(body="|".join(body_versions)), version)
	p = body_parameters(m.group(1))
	p["h"] = int(m.group(2))
	return p
    
def riser_parameters(version):
    """extract the parameters for sample risers"""
    m = re.match("(LS|SS)([\d]+)", version)
    p = {}
    p["big_stage"] = "LS" == m.group(1)
    p["h"] = int(m.group(2))
    return p

def openscad_recipe(**kwargs):
    output = "\t" + "openscad -o $@"
    for name, value in kwargs.iteritems():
        try:
            float(value)
        except ValueError:
            # numbers and booleans are OK, but strings need to be double-quoted on the command line.
            if value not in ["true", "false"]:
                value = '"{}"'.format(value)
        if type(value) == type(True): #need to convert boolean values
            value = "true" if value else "false"
        output += " -D '{name}={value}'".format(name=name, value=str(value))
    output += " $<\n"
    return output
    
def merge_dicts(*args):
    """Merge dictionaries together into a single output."""
    out = args[0].copy()
    for a in args[1:]:
        out.update(a)
    return out

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate the Openflexure Microscope makefile")
    parser.add_argument("--version_numstring", help="Override the defined version string", default=None)
    args = parser.parse_args()
    
    extra_defines = {}
    if args.version_numstring:
        extra_defines['version_numstring'] = args.version_numstring
        
    def openscad_recipe_baked(**kwargs):
        """An openscad recipe, with additional definitions baked in."""
        return openscad_recipe(**merge_dicts(extra_defines, kwargs))
    
    with open("Makefile","w") as makefile:
        def M(line):
            makefile.write(line + "\n")
        M("# Makefile for the openflexure microscope")
        M("# Generated by generate_makefile.py")
        M(".PHONY: all cleanstl")
        M("")
        M("SOURCE = openscad")
        M("OUTPUT = builds")
        M("")
        M("body_versions = " + " ".join(body_versions))
        M("optics_versions = " + " ".join(optics_versions))
        M("sample_riser_versions = " + " ".join(sample_riser_versions))
        M("slide_riser_versions = " + " ".join(slide_riser_versions))
        M("")
        M("TOOLS := actuator_assembly_tools lens_tool")
        M("TOOLS := $(TOOLS) picamera_2_cover picamera_2_gripper picamera_2_lens_gripper actuator_drilling_jig")
        M("ACCESSORIES := picamera_2_cover $(sample_riser_versions:%=sample_riser_%) $(slide_riser_versions:%=slide_riser_%) microscope_stand microscope_stand_no_pi motor_driver_case back_foot")
        M("COMMONPARTS := feet feet_tall gears sample_clips small_gears")
        M("BODIES := $(body_versions:%=main_body_%)")
        M("OPTICS := $(optics_versions:%=optics_%) camera_platform_picamera_2_LS65 camera_platform_6led_LS65 lens_spacer_picamera_2_pilens_LS65 lens_spacer_picamera_2_pilens_LS75")
        M("ILLUMINATIONS := illumination_dovetail condenser")
        M("ALLPARTS := $(COMMONPARTS) $(TOOLS) $(BODIES) $(ILLUMINATIONS) $(OPTICS) $(ACCESSORIES)")
        M("ALLSTLFILES := $(ALLPARTS:%=$(OUTPUT)/%.stl)")
        M("")
        M("parameters_file := $(SOURCE)/microscope_parameters.scad")
        M("utilities_file := $(SOURCE)/utilities.scad")
        M("all_deps := $(parameters_file) $(utilities_file) 			#All targets depend on these")
        M("")
        M("all: $(ALLSTLFILES)")
        M("")
        M("cleanstl:")
        M("\t"+"rm $(STLFILES)")
        M("")
        M("#parameter and utilities files affect everything")
        M("$(OUTPUT)/%.stl: $(all_deps)")
        M("")
        M("main_body_dep_names := compact_nut_seat dovetail logo z_axis")
        M("main_body_deps := $(main_body_dep_names:%=$(SOURCE)/%.scad)")
        for version in body_versions:
            M("$(OUTPUT)/main_body_" + version + ".stl: $(SOURCE)/main_body.scad $(main_body_deps)")
            M(openscad_recipe_baked(**body_parameters(version)))
        M("")
        for version in body_versions:
            M("$(OUTPUT)/illumination_dovetail_" + version + ".stl: $(SOURCE)/illumination_dovetail.scad $(main_body_deps) $(SOURCE)/illumination.scad")
            M(openscad_recipe_baked(**body_parameters(version)))
            M("$(OUTPUT)/condenser_" + version + ".stl: $(SOURCE)/condenser.scad $(main_body_deps) $(SOURCE)/illumination.scad")
            M(openscad_recipe_baked(**body_parameters(version)))
        M("")
        M("optics_dep_names := dovetail cameras/camera")
        M("optics_deps := $(optics_dep_names:%=$(SOURCE)/%.scad)")
        for version in optics_versions:
            M("$(OUTPUT)/optics_" + version + ".stl: $(SOURCE)/optics.scad $(optics_deps)")
            M(openscad_recipe_baked(**optics_module_parameters(version)))
        M("")
        for b in ["LS65", "LS75"]:
            for n in ["camera_platform_picamera_2", "lens_spacer_picamera_2_pilens"]:
                M("$(OUTPUT)/{}_{}.stl: $(SOURCE)/{}.scad $(optics_deps)".format(n, b, n.split("_picamera_")[0]))
                M(openscad_recipe_baked(camera="picamera_2", optics="pilens", **body_parameters(b)))
        for b in ["LS65", "LS75"]:
            n = "camera_platform_6led"
            M("$(OUTPUT)/{}_{}.stl: $(SOURCE)/{}.scad $(optics_deps)".format(n, b, n.split("_6led")[0]))
            M(openscad_recipe_baked(camera="6led", optics="pilens", **body_parameters(b)))
        M("riser_dep_names := main_body")
        M("riser_deps := $(optics_dep_names:%=$(SOURCE)/%.scad)")
        for version in sample_riser_versions:
            M("$(OUTPUT)/sample_riser_" + version + ".stl: $(SOURCE)/sample_riser.scad $(riser_deps)")
            M(openscad_recipe_baked(**riser_parameters(version)))
        for version in slide_riser_versions:
            M("$(OUTPUT)/slide_riser_" + version + ".stl: $(SOURCE)/slide_riser.scad $(riser_deps)")
            M(openscad_recipe_baked(**riser_parameters(version)))
        M("")
        M("stand_dep_names := main_body")
        M("stand_deps := $(optics_dep_names:%=$(SOURCE)/%.scad)")
        for version in stand_versions:
            M("$(OUTPUT)/microscope_stand_" + version + ".stl: $(SOURCE)/microscope_stand.scad $(stand_deps)")
            M(openscad_recipe_baked(**stand_parameters(version)))
        M("")
        M("$(OUTPUT)/picamera_2_%.stl: $(SOURCE)/cameras/picamera_2_%.scad $(all_deps)")
        M(openscad_recipe_baked(camera="picamera_2"))
        M("")
        M("$(OUTPUT)/feet_tall.stl: $(SOURCE)/feet.scad $(all_deps)")
        M(openscad_recipe_baked(foot_height=26))
        M("")
        M("$(OUTPUT)/actuator_assembly_tools.stl: $(SOURCE)/actuator_assembly_tools.scad $(all_deps)")
        M(openscad_recipe_baked(foot_height=26))
        M("")
        M("$(OUTPUT)/%.stl: $(SOURCE)/%.scad $(all_deps)")
        M(openscad_recipe_baked())
        M("")
