import xml

import cv2
from pathlib import Path
import pytesseract
from pytesseract import Output

import re
from pprint import pprint

import inflection
import xmltodict
import numpy as np
import pandas as pd
from operator import itemgetter

xml_annotations_path = Path("../xml_annotations/")
annotations_path = Path("../annotations/")
screenshots_path = Path("../screenshots/")


def get_widget_subclass(widget_class):
    return widget_class.split(".")[-1]


columns = ["widget_type", "classname", "xmin", "ymin", "xmax", "ymax", "text", "group"]


component_type_map = {
    "Spinner": "dropdown_menu",
    "TextView": "label",
    "EditText": "text_field",
    "CheckBox": "checkbox",
    "Button": "button",
    "Switch": "switch",
    "ImageButton": "icon_button",
    "CheckedTextView": "checkbox",
    "ProgressBar": "progress",
    "ToggleButton": "toggle_button",
    "Chip": "chip",
    "SeekBar": "slider",
    "ImageView": "image",
    "RadioButton": "radio_button"
}

checkable = ["checkbox", "switch", "toggle_button", "radio_button"]

layout_widgets = ["FrameLayout",
                  "ScrollView",
                  "LinearLayout",
                  "ViewGroup",
                  "LinearLayoutCompat",
                  "View",
                  "ViewPager",
                  "DrawerLayout",
                  "HorizontalScrollView",
                  "RelativeLayout"]

layout_type_map = dict(zip(layout_widgets, map(inflection.underscore, layout_widgets)))

def parse_annotation(image, obj):
    arr = []
    
    def extract(obj, arr, group):
        if isinstance(obj, dict):
            if "@class" in obj.keys():
                subclass = get_widget_subclass(obj["@class"])
                
                
                
                text = obj.get("@text", "")
                xmin, ymin, xmax, ymax = map(int, re.findall(r"\d+", obj["@bounds"]))
                
                
                if subclass in layout_widgets:
                    widget_type = "layout"
                    classname = layout_type_map.get(subclass, subclass)
                else:
                    widget_type = "component"
                    classname = component_type_map.get(subclass, subclass)
                
                if classname in checkable:
                    if classname == "slider":
                        classname += "_enabled" if obj["@checked"] == "true" else "_disabled"
                    else:
                        classname += "_checked" if obj["@checked"] == "true" else "_unchecked"
                    
                if classname == "label":
                    cropped_image = image[ymin:ymax, xmin:xmax]
                    d = pytesseract.image_to_data(cropped_image, output_type=Output.DICT)
                    bb_i = 0 if len(d['left']) == 1 else 1
                    (x, y, w, h) = (d['left'][bb_i], d['top'][bb_i], d['width'][bb_i], d['height'][bb_i])
                    xmin, ymin = xmin+x, ymin+y
                    xmax, ymax = xmin+w, ymin+h
                
                arr.append([widget_type, classname, xmin, ymin, xmax, ymax, text, group])
            
            for k, v in obj.items():                
                if isinstance(v, (dict, list)):
                    extract(v, arr, group)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                extract(item, arr, f"{group}.{i+1}")

    try:
        extract(obj, arr, "1")
    except Exception as e:
        print(e.with_traceback())
    
    return arr    
    

def store_annotations(filename):
    
    full_xml_file = xml_annotations_path/f"full_{filename}.xml"
    xml_file = xml_annotations_path/f"{filename}.xml"
    image_file = screenshots_path/f"{filename}.png"
    
    image = cv2.imread(str(image_file))
    
    
    with open(full_xml_file) as fd:
        doc = xmltodict.parse(fd.read())
        annotations = parse_annotation(image, doc)
        pd.DataFrame(annotations, columns=columns).to_csv(annotations_path/f"full_{filename}.csv")
        
    with open(xml_file) as fd:
        doc = xmltodict.parse(fd.read())
        annotations = parse_annotation(image, doc)
        pd.DataFrame(annotations, columns=columns).to_csv(annotations_path/f"{filename}.csv")