import UnityPy
import json
import argparse
import os
import UnityPy
from PIL import Image
import hashlib
import math

def unpack_all_assets(source_folder: str, destination_folder: str):
    # iterate over all files in source folder
    for root, dirs, files in os.walk(source_folder):
        for file_name in files:
            # generate file_path
            file_path = os.path.join(root, file_name)
            # load that file via UnityPy.load
            env = UnityPy.load(file_path)

            # iterate over internal objects
            for obj in env.objects:
                print(f"Parsed data has been saved to {obj.path_id}")



destination_folder = "./extracted_data";

def main(): 
    parser = argparse.ArgumentParser()
    parser.add_argument("--sheet_prefix", default="images/sprite-sheet")
    parser.add_argument("--datafile", default=r"/mnt/e/steamLibrary/steamapps/common/FOUNDRY/foundry_Data/StreamingAssets/AssetBundles/foundry_main_bundle")
    parser.add_argument("--outfile", default="data.json")
    parser.add_argument("--write_sprites", action="store_true")
    args = parser.parse_args()


    extract_all_MonoBehaviour(args.datafile)    
    parsed_data = parseMonoBehaviour()

    removeBrokenItemsAndrecipes(parsed_data)

    addSprites(args.datafile, parsed_data, args.sheet_prefix, args.write_sprites)
    # Save the parsed data as JSON
    with open("./data/latest.json", "w") as json_file:
        json.dump(parsed_data, json_file, indent=4, sort_keys=True)
        print(f"Parsed data has been saved to {json_file.name}")    

    return

def removeBrokenItemsAndrecipes(parsed_data: dict):
    """
    Removes items and recipes that are broke
    """

    # Remove items that are not present in the parsed data
    for item_key in list(parsed_data.keys()):
        
        if not isinstance(parsed_data[item_key], dict):
            continue
        for value_key in list(parsed_data[item_key].keys()):
            if not isinstance(parsed_data[item_key][value_key], dict):
               continue
            value = parsed_data[item_key][value_key]
            if 'icon_identifier' not in value:
                print(f"Skipping {item_key}: {value_key} because it has no icon_identifier.")
                continue
            if value['icon_identifier'].startswith("plant"):
                print(f"Removing {item_key}: {value_key} because it is a plant. which are broken.")
                del parsed_data[item_key][value_key]


def extract_all_MonoBehaviour(datafile: str):
    if not os.path.exists(destination_folder):
        env = UnityPy.load(datafile)
        for path,obj in env.container.items():
            if obj.type.name == "MonoBehaviour":      
                # save decoded data
                tree = obj.read_typetree()
                dest = os.path.join(destination_folder, *path.split("/"))
                dest += ".json"
                # make sure that the dir of that path exists
                os.makedirs(os.path.dirname(dest), exist_ok = True)
            
                with open(dest, "wt", encoding = "utf8") as f:
                    json.dump(tree, f, ensure_ascii = False, indent = 4)
            # lets also extract the sprites
            if obj.type.name == "Sprite":
                if not "512" in path and not "clock" in path:
                    continue
                data = obj.read()
                # create dest based on original path
                dest = os.path.join(destination_folder, *path.split("/"))
                # make sure that the dir of that path exists
                os.makedirs(os.path.dirname(dest), exist_ok = True)
                # correct extension
                dest, ext = os.path.splitext(dest)
                dest = dest + ".png"
                # save the image
                data.image.save(dest)


def parseMonoBehaviour() -> dict:
    # Parse the data
    parsed_data = {}
    parsed_data['items'] = {}
    parsed_data['recipes'] = {}
    for root, dirs, files in os.walk(destination_folder):
        path = root[len(destination_folder) + 1:].replace(os.sep, "/")
        if path.lower().startswith("Assets/FoundryTemplates/Items".lower()):
            for file in files:
                parsed_data['items'].update(parseItems(path, file))
        if path.lower().startswith("Assets/FoundryTemplates/elements".lower()):
            for file in files:
                parsed_data['items'].update(parseLiquid(path, file))
    for root, dirs, files in os.walk(destination_folder):
        path = root[len(destination_folder) + 1:].replace(os.sep, "/")
        if path.lower().startswith("Assets/FoundryTemplates/CraftingRecipes/".lower()):
            for file in files:
                parsed_data['recipes'].update(parseRecipes(parsed_data, path, file))
    parsed_data.update(addExtraData(parsed_data))        
    return parsed_data
    

def parseRecipes(parsed_data : dict, path: str, file: str) -> dict:
    """
    Parses individual recipe files and returns the parsed data as a dictionary.
    """
    file_path = os.path.join(destination_folder, path,  file)
    recipe_data = {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)
            if json_data.get("isHiddenRecipe") == 1:
                return {}
            recipe_data['name'] = json_data.get("identifier", "Unknown")
            recipe_data['localized_name'] = {
                "en":json_data.get("name", "Unknown")
            }
            recipe_data['type'] = 'recipe'
            recipe_data['enabled'] = False
            recipe_data['icon_identifier'] = json_data.get("icon_identifier", "")
            recipe_data['energy_required'] = json_data.get("timeMs", 1500) / 1000
            recipe_data['category'] = json_data.get("tags", "Unknown")
            # remove the category "character" from the array
            if "character" in recipe_data['category']:
                recipe_data['category'].remove("character")
            recipe_data['order'] = 'a'
            recipe_data['subgroup'] = json_data.get("subgroup", "all")
            recipe_data['ingredients'] = json_data.get("input_data", [])
            # Change the "indentifier" to the "name"
            for ingredient in recipe_data['ingredients']:
                if 'percentage_str' in ingredient:
                    ingredient.pop('percentage_str')
                if 'identifier' in ingredient:
                    ingredient['name'] = ingredient.pop('identifier')
            # Fluid/liquid ingredients (e.g. molten metal fed into a casting
            # machine) live in a separate "elemental" list keyed by
            # amount_str rather than amount/percentage_str.
            for ingredient in json_data.get("inputElemental_data", []):
                recipe_data['ingredients'].append({
                    "name": ingredient["identifier"],
                    "amount": float(ingredient.get("amount_str", 0)),
                })

            recipe_data['results'] = json_data.get("output_data", [])
            # Change the "indentifier" to the "name"
            for result in recipe_data['results']:
                if 'percentage_str' in result:
                    result.pop('percentage_str')
                if 'identifier' in result:
                    result['name'] = result.pop('identifier')
                if result['name'] not in parsed_data['items']:
                    print(f"Warning: {result['name']} not found in items. Skipping result.")
                    return {}
            # Fluid/liquid results, same "elemental" list as above.
            for result in json_data.get("outputElemental_data", []):
                if result["identifier"] not in parsed_data['items']:
                    print(f"Warning: {result['identifier']} not found in items. Skipping result.")
                    continue
                recipe_data['results'].append({
                    "name": result["identifier"],
                    "amount": float(result.get("amount_str", 0)),
                })
            recipe_data['result'] = json_data.get("result", {})
            
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        
    return {recipe_data['name']: recipe_data}

def parseItems(path: str, file: str) -> dict:
    """
    Parses individual item files and returns the parsed data as a dictionary.
    """
    file_path = os.path.join(destination_folder, path,  file)
    item_data = {}           
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)
            if json_data.get("isHiddenItem") == 1:
                item_data['hidden'] = True
            else:
                item_data['hidden'] = False
            item_data['name'] = json_data.get("identifier", "Unknown")
            item_data['localized_name'] = {
                "en":json_data.get("name", "Unknown")
            }
            item_data['stack_size'] =  json_data.get("stackSize", 0)
            item_data['fuel_value'] = json_data.get("burnable_fuelValueKJ_str", 0)
            item_data['type'] = 'item'
            item_data['group'] = json_data.get("itemCategoryIdentifier", "all")
            if item_data['group'] == "":
                item_data['group'] = json_data.get("modIdentifier", "Unknown") + "_" + os.path.basename(path)
            item_data['order'] = 'a'
            if item_data['fuel_value'] != 0:
                item_data['fuel_category'] = "chemical"
                item_data['fuel_residual'] = json_data.get("burnable_residualItemTemplate_str", "")
            else:
                item_data['fuel_category'] = ""
                item_data['fuel_residual'] = ""
            item_data['icon_identifier'] = json_data.get("icon_identifier", "")
            item_data['flags'] = json_data.get("flags", 0)
            
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        
    return {item_data['name']: item_data}

def parseLiquid(path: str, file: str) -> dict:
    """
    Parses individual liquid files and returns the parsed data as a dictionary.
    """
    file_path = os.path.join(destination_folder, path,  file)
    item_data = {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)
            if json_data.get("isHiddenItem") == 1:
                item_data['hidden'] = True
            else:
                item_data['hidden'] = False
            item_data['name'] = json_data.get("identifier", "Unknown")
            item_data['localized_name'] = {
                "en":json_data.get("name", "Unknown")
            }
            item_data['stack_size'] =  json_data.get("stackSize", 0)
            item_data['type'] = 'fluid'
            item_data['fuel_value'] = 0
            item_data['group'] = json_data.get("itemCategoryIdentifier", "all")
            item_data['order'] = 'a'
            item_data['icon_identifier'] = json_data.get("icon_identifier", "")
            item_data['fuel_category'] = ""
            item_data['fuel_residual'] = ""
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
    return {item_data['name']: item_data}

def addExtraData(parsed_data) -> dict:
    """
    Adds extra data to the parsed data.
    """
    extra_data = {
    "sprites": {
        "extra": {
            "clock": {
                "icon_col": 0,
                "icon_row": 0,
                "name": "time"
            }
        },
        "hash": "2",
        "height": 1024,
        "width": 1024
    },
    "modules": [],
    "fuel": getFuelData(parsed_data),
    "groups": { 
        "all": {
            "order": "z",
            "subgroups": {
                "all": "a"
            }
        },
        **getGroups(parsed_data)
        },
    "belts": {
        "_base_conveyor_i": {
            "icon_col": 10,
            "icon_row": 2,
            "icon_identifier": "conveyor_i",
            "localized_name": {
                "en": "Conveyor I"
            },
            "name": "_base_conveyor_i",
            "speed": 160
        },
        "_base_conveyor_ii": {
            "icon_col": 11,
            "icon_row": 2,
            "icon_identifier": "conveyor_ii",
            "localized_name": {
                "en": "Conveyor II"
            },
            "name": "_base_conveyor_ii",
            "speed": 320
        },
        "_base_conveyor_iii": {
            "icon_col": 12,
            "icon_row": 2,
            "icon_identifier": "conveyor_iii",
            "localized_name": {
                "en": "Conveyor III"
            },
            "name": "_base_conveyor_iii",
            "speed": 640
        },
        "_base_conveyor_iv": {
            "icon_col": 13,
            "icon_row": 2,
            "icon_identifier": "conveyor_iv",
            "localized_name": {
                "en": "Conveyor IV"
            },
            "name": "_base_conveyor_iv",
            "speed": 1280
        },
    },
    "miners": {
        "drone_miner_i": {
            "crafting_categories": [
                "mining_ore"
            ],
            "mining_speed": 50,
            "energy_usage": 50000,
            "mining_power": 1,
            "icon_identifier": "drone_miner_i",
            "icon_col": 15,
            "icon_row": 3,
            "localized_name": {
                "en": "Drone Miner I"
            },
            "module_slots": 0,
            "name": "Drone Miner I",
            "overrides": {}
        },
        "drone_miner_ii": {
            "crafting_categories": [
                "mining_ore"
            ],
            "mining_speed": 80,
            "energy_usage": 100000,
            "mining_power": 1,
            "icon_identifier": "drone_miner_ii",
            "icon_col": 15,
            "icon_row": 3,
            "localized_name": {
                "en": "Drone Miner II"
            },
            "module_slots": 0,
            "name": "Drone Miner II",
            "overrides": {}
        },
        "pump_jack": {
            "crafting_categories": [
                "mining_fluid"
            ],
            "mining_speed": 1800,
            "energy_usage": 200000,
            "mining_power": 1,
            "icon_identifier": "pumpjack_i",
            "icon_col": 2,
            "icon_row": 10,
            "localized_name": {
                "en": "Pumpjack I"
            },
            "module_slots": 0,
            "name": "Pumpjack I",
            "overrides": {}
        }
    },
        "machine":
        {
            **getMachines(parsed_data)
        },
        "resource" : {
            **getResources(parsed_data)
        },
            "tiers": [
        {
            "name": "T1",
            "displayName": "Tier 1",
            "prefix": "T1;",
            "recipes": {
                "_base_xf_plates_t1": True,
                "_base_technum_rods_t1": True,
                "_base_steel_t1": True
            },
            "icon_col": 0,
            "icon_row": 11
        },
        {
            "name": "T2",
            "displayName": "Tier 2",
            "prefix": "T2;",
            "recipes": {
                "_base_ore_xenoferrite": True,
                "_base_ore_technum": True,
                "_base_xf_plates_t2": True,
                "_base_technum_rods_t2": True,
                "_base_steel_t2": True
            },
            "icon_col": 2,
            "icon_row": 9
        },
        {
            "name": "T3",
            "displayName": "Tier 3",
            "prefix": "T3;",
            "recipes": {
                "_base_ore_xenoferrite": True,
                "_base_ore_technum": True,
                "_base_bfm_te": True,
                "_base_bfm_xf":True,
                "_base_xf_plates_t3": True,
                "_base_technum_rods_t3": True,
                "_base_steel_t2": True
            },
            "icon_col": 1,
            "icon_row": 14
        }
    ],
    }
    
    return extra_data

def getResources(parsed_data) -> dict:
    return  {
        "_resource_base_rubble_technum": {
            "category": "ore",
            "icon_identifier": "ore_rubble_technum",
            "localized_name": {
                "en": "Technum Ore Rubble"
            },
            "minable": {
                "mining_time": 1,
                "results": [
                    {
                        "amount": 1,
                        "name": "_base_rubble_technum"
                    }
                ]
            },
            "name": "_resource_base_rubble_technum"
        },
        "_resource_base_rubble_xenoferrite": {
            "category": "ore",
            "icon_identifier": "ore_rubble_xenoferrite",
            "localized_name": {
                "en": "Xenoferrite Ore Rubble"
            },
            "minable": {
                "mining_time": 1,
                "results": [
                    {
                        "amount": 1,
                        "name": "_base_rubble_xenoferrite"
                    }
                ]
            },
            "name": "_resource_base_rubble_xenoferrite"
        },
        "_resource_base_rubble_ignium": {
            "category": "ore",
            "icon_identifier": "ore_rubble_ignium",
            "localized_name": {
                "en": "Ignium Ore Rubble"
            },
            "minable": {
                "mining_time": 1,
                "results": [
                    {
                        "amount": 1,
                        "name": "_base_rubble_ignium"
                    }
                ]
            },
            "name": "_resource_base_rubble_ignium"
        },
        "_resource_base_ore_mineral_rock": {
            "category": "ore",
            "icon_identifier": "mineral_rock",
            "localized_name": {
                "en": "Mineral Rocks"
            },
            "minable": {
                "mining_time": 1,
                "results": [
                    {
                        "amount": 1,
                        "name": "_base_ore_mineral_rock"
                    }
                ]
            },
            "name": "_resource_base_ore_mineral_rock"
        },
        "_resource_base_olumite": {
            "category": "fluid",
            "iconidentifier": "fluid_olumite",
            "localized_name": {
                "en": "Crude Olumite"
            },
            "minable": {
                "mining_time": 1,
                "results": [
                    {
                        "amount": 1,
                        "name": "_base_olumite"
                    }
                ]
            },
            "name": "_resource_base_olumite"
        },
        "_resource_base_water": {
            "category": "fluid",
            "icon_identifier": "water",
            "localized_name": {
                "en": "Water"
            },
            "minable": {
                "mining_time": 1,
                "results": [
                    {
                        "amount": 1,
                        "name": "_base_water"
                    }
                ]
            },
            "name": "_resource_base_water"
        }
    }

def getMachines(parsed_data) -> dict:
    """
    Extracts machine data from the parsed items and recipes.
    """
    machines = {}
    for root, dirs, files in os.walk(destination_folder):
        path = root[len(destination_folder) + 1:].replace(os.sep, "/")
        if path.lower().startswith("assets/foundrytemplates/buildableobjects".lower()):
            for file in files: 
                machines.update(getMachinesFromFile(path, file, machines, parsed_data))

    return machines

def getMachinesFromFile(path: str, file: str, machines: dict, parsed_data) -> dict:
    """
    Parses individual machine files and returns the parsed data as a dictionary.
    """
    file_path = os.path.join(destination_folder, path,  file)
    machine_data = {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)
            if json_data.get("producer_recipeType_tags") == []:
                return {}
            if json_data.get("type") in  [31, 41, 62, 81, 69]:  # Type 31 is are doors which for some reason got taggd with assmebler
                return {}
            modId = json_data.get("modIdentifier", "_base")
            crafting_categories = json_data.get("producer_recipeType_tags")
            machine_data["crafting_categories"] = crafting_categories 
            
            machine_data['name'] = json_data.get("identifier", "Unknown")
            machine_data['localized_name'] = {
                "en": json_data.get("m_Name", "Unknown")[:-4] # Remove the " BOT" at the end
            }
            try:
                machine_data['energy_usage'] = int(json_data.get("energyConsumptionKW_str", 0)) * 1000
            except ValueError:
                print(f"Invalid energy consumption value in {file_path}: {json_data.get('energyConsumptionKW_str', 0)}")
                return {}
            
            machine_data['crafting_speed'] = float(json_data.get("producer_recipeTimeModifier_str", "1"))
            if json_data.get("autoProducer_recipeType_tag", "unkown") != "":
                machine_data["crafting_categories"] = [json_data.get("autoProducer_recipeType_tag", "unkown")]
                machine_data['crafting_speed'] = float(json_data.get("autoProducer_recipeTimeModifier_str", ""))

            machine_data['icon_identifier'] = parsed_data['items'][machine_data['name']]['icon_identifier']
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")        
    return {machine_data['name'] : machine_data}

def getFuelData(parsed_data) -> list:
    """
    Extracts fuel data from the parsed items.
    """
    fuel_data = []
    for item in parsed_data.get('items', {}).values():
        if item['fuel_value'] != '' and item['fuel_value'] != 0:
            if item['flags'] & 0b000010000:
                fuel_data.append(item['name'])
    return fuel_data

def getGroups(parsed_data) -> dict:
    """
    Extracts unique groups from the parsed items and recipes.
    """
    groups = set()
    for item in parsed_data.get('items', {}).values():
        if item['group'].startswith("_base"):
            groups.add(item['group'])
    toReturn = {}
    for item in sorted(groups):
        toReturn[item] = {
            "order": "a",
            "subgroups": {
                "all": "a"
            }
        }
    return toReturn

def addSprites(file_path, parsed_data, sheet_prefix: str, write_sprites: bool):
    images = []
    files = []
    for root, dirs, files in os.walk(destination_folder):
        sorted_files = sorted(files, key=lambda x: x.lower())        
        for file in sorted_files:
            if file.lower() == "icons8-clock-100.png":
                # Special case for clock icon at it first in line
                images.insert(0, (file, Image.open(os.path.join(root, file)).convert("RGBA").resize((512, 512))))
            if file.lower().endswith('air_intake_base_512.png'):
                1 + 1    
            if file.lower().endswith("512.png"):
                if addToSprite(parsed_data,file):
                    img = (file, Image.open(os.path.join(root, file)).convert("RGBA"))
                    images.append(img)



    sprite_sheet = create_sprite_sheet(parsed_data, images, columns=16)

    if sprite_sheet:
        # Generate a 4-digit hash of the sprite sheet
        with open("sprite_sheet.png", "rb") as f:
            sprite_sheet_hash = hashlib.md5(f.read()).hexdigest()[:5]
        print(f"Sprite sheet hash: {sprite_sheet_hash}")
        dest_path = f"{sheet_prefix}-{sprite_sheet_hash}.png"
        # os.rename() raises on Windows (unlike POSIX) if dest already
        # exists, e.g. when re-running with an unchanged sprite sheet.
        if os.path.exists(dest_path):
            os.remove(dest_path)
        os.rename("sprite_sheet.png", dest_path)
        parsed_data['sprites']['hash'] = sprite_sheet_hash
        parsed_data['sprites']['width'] = sprite_sheet.width
        
        parsed_data['sprites']['height'] = sprite_sheet.height
        print(f"Sprite sheet with width {sprite_sheet.width} and height {sprite_sheet.height} created.")
        print(f"Saved {sheet_prefix}-{sprite_sheet_hash}.png")


def create_sprite_sheet(parsed_data, images : tuple[str, Image.Image], columns=18, padding=0, bg_color=(0, 0, 0, 0)):
    if not images:
        print("No images found.")
        return None

    # Assume all images are the same size
    img_width, img_height = images[0][1].size
    rows = (len(images) + columns - 1) // columns  # ceil division

    sheet_width = columns * img_width + (columns - 1) * padding
    sheet_height = rows * img_height + (rows - 1) * padding

    sheet = Image.new("RGBA", (sheet_width, sheet_height), bg_color)

    for index, tuple in enumerate(images):
        img = tuple[1]
        x = (index % columns) * (img_width + padding)
        y = (index // columns) * (img_height + padding)
        # if index > columns * columns:
        #     break
        sheet.paste(img, (x, y))
        addToData(parsed_data, tuple, index, (index % columns), (index // columns))
    
    # Resize the sprite sheet to a maximum width of 1024 pixels
    height = math.ceil(1024 / sheet.width * sheet.height)
    sheet = sheet.resize((1024, int(height)), Image.Resampling.LANCZOS)
    sheet.save("sprite_sheet.png")    
    return sheet

def addToData(parsed_data,tuple, index, x, y):
    """
    Adds the sprite data to the parsed data.
    """
    filename = tuple[0]
    for category in ['items', 'recipes', 'resource', 'machine', 'belts', 'miners']:
        for item in parsed_data.get(category, {}).values():
            if 'icon_identifier' in item and item['icon_identifier'] == filename[:-8].replace(" ", "_"):
                item['icon_col'] = x
                item['icon_row'] = y

def addToSprite(parsed_data, file: str) -> bool:
    """
    Adds the sprite to the parsed data if it is not already present.
    """
    toAdd = ['items' , 'recipes', 'resource', 'machine', 'belts', 'miners']
    for key_name in toAdd:
        if key_name not in parsed_data:
          print(f"Warning: {key_name} not found in parsed data. Skipping sprite addition.")
        dataSet = parsed_data[key_name]
        for item in dataSet.values():
            if 'icon_identifier' in item and item['icon_identifier'] == file[:-8].replace(" ", "_"):
                return True

    return False

if __name__ == "__main__":
    main()
