from collections import defaultdict
import re

def detect_type(text: str):
    if not text:
        return None

    t = text.lower()
    scores = defaultdict(int)

    # ---------------- PLANTS ----------------
    plant_keywords = [
        "plant", "flower", "petal", "leaf", "leaves", "stem", "seed",
        "grass", "weed", "shrub", "tree", "bark", "root", "rosette",
        "wildflower", "botanical", "algae", "lichen", "moss", "fungi",
        "photosynthesis", "pollination", "woodlands", "evergreen", "deciduous",
        "gardens"
    ]
    for k in plant_keywords:
        if k in t:
            scores["Plant"] += 3

    # ---------------- INVERTEBRATES ----------------
    invertebrate_keywords = [
        "invertebrate", "cnidarian", "jellyfish", "coral", "anemone",
        "medusa", "arthropod", "crustacean", "mollusk", "mollusc",
        "octopus", "squid", "snail", "slug", "worm", "annelid",
        "plankton", "echinoderm", "starfish", "sea star", "urchin"
    ]
    for k in invertebrate_keywords:
        if k in t:
            scores["Invertebrate"] += 4

    # ---------------- FISH ----------------
    fish_keywords = [
        "fish", "shark","whale shark", "ray", "eel", "gill", "fins", "school",
        "cartilaginous", "bony fish", "teleost", "swim bladder",
        "lateral line", "spawning", "aquatic", "freshwater", "saltwater",
        "turtles", "turtle", "sea turtles", "sea turtle", "tentacles"
    ]
    for k in fish_keywords:
        if k in t:
            scores["Fish"] += 9

    # ---------------- AQUATIC MAMMALS ----------------
    aquatic_mammals = [
        "whale", "dolphin", "porpoise", "seal", "walrus",
        "manatee", "dugong", "cetacean", "pinniped", "blubber",
        "echolocation", "fluke", "flipper", "baleen", "toothed whale", 
        "orca", "narwhal", "sea lion"
    ]
    for k in aquatic_mammals:
        if k in t:
            scores["Aquatic Mammal"] += 10

    # ---------------- MAMMALS ----------------
    mammal_keywords = [
        "mammal", "fur", "hair", "gestation", "placental",
        "hooves", "antlers", "horns", "teeth", "paws",
        "herbivore", "carnivore", "omnivore",
        "kilograms", "centimeters", "lactation",
        "mane", "tail", "snout", "ears", "tusks", 
        "dewlap", "scrotum", "udder", "teats",
        "calf", "fawn", "juvenile",
        "herd", "troop", "pack", "nocturnal", "diurnal",
        "herbivorous", "carnivorous", "omnivorous", "insectivorous",
        "centimeters", "meters", "shoulder height",
        "antelope", "bovid", "canid", "primate", "ungulate",
        "territorial", "otter", "badger", "weasel", "mongoose", 
        "mammals", "badgers", "gorilla", "kangaroo", "elephants", "elephant"
    ]

    for k in mammal_keywords:
        if k in t:
            scores["Mammal"] += 7

    # ---------------- BIRDS ----------------
    bird_keywords = [
        "bird", "avian", "feathers", "beak", "bill",
        "wings", "flight", "nest", "eggs",
        "migratory", "songbird", "raptor",
        "flight", "wingspan", "nest", "flock",
        "scavenger",
        "vulture", "crane", "ostrich", "lovebird", "falcon"
    ]
    for k in bird_keywords:
        if k in t:
            scores["Bird"] += 5

    # ---------------- REPTILES ----------------
    reptile_keywords = [
        "reptile", "snake", "lizard", "crocodile",
        "alligator", "turtle", "tortoise",
        "gecko", "iguana", "scales", "cold-blooded"
    ]
    for k in reptile_keywords:
        if k in t:
            scores["Reptile"] += 3

    # ---------------- AMPHIBIANS ----------------
    amphibian_keywords = [
        "amphibian", "frog", "toad", "newt", "salamander",
        "tadpole", "metamorphosis"
    ]
    for k in amphibian_keywords:
        if k in t:
            scores["Amphibian"] += 3

    # ---------------- INSECTS ----------------
    insect_keywords = [
        "insect", "butterfly", "moth", "bee", "wasp",
        "ant", "beetle", "dragonfly", "grasshopper",
        "mosquito", "fly", "larva", "caterpillar",
        "pupa", "thorax", "abdomen",
        "compound eye", "antennae", "beetles", "arachnid", "spider", "mite", "tick",
        "honeycomb", "swarm", "larvae", "pollen", "hoverfly", "projection", "pupate"
    ]
    for k in insect_keywords:
        if k in t:
            scores["Insect"] += 5

    # ---------------- SCIENTIFIC NAME HEURISTICS ----------------
    sci_patterns = {
        "Plant": [r"\baceae\b", r"\blanceolata\b", r"\bofficialis\b"],
        "Fish": [r"\bidae\b"],
        "Invertebrate": [r"\bcnidaria\b", r"\bcephalopoda\b"],
        "Mammal": [r"\bidae\b", r"\bssp\.\b"],
        "Bird": [r"\bidae\b", r"\baves\b"],
        "Reptile": [r"\bidae\b", r"\bsquamata\b"],
        "Amphibian": [r"\bidae\b", r"\banura\b"],
    }

    for category, patterns in sci_patterns.items():
        for p in patterns:
            if re.search(p, t):
                scores[category] += 2

    # ---------------- RULES ----------------
    if scores["Invertebrate"] > 4:
        for k in ["Bird", "Mammal", "Reptile", "Amphibian"]:
            scores[k] = 0

    if (scores["Mammal"] > 0 and scores["Aquatic Mammal"] > 0) or (scores["Bird"] > 0 and scores["Fish"] > 0) or (scores["Invertebrate"] > 0 and scores["Fish"] > 0):
        scores["Insect"] = 0

    # ---------------- PRIORITY ----------------
    priority = [
        "Aquatic Mammal",
        "Bird",
        "Fish",
        "Mammal",
        "Insect",
        "Invertebrate",
        "Plant",
        "Amphibian",
        "Reptile",
    ]

    best_type = None
    best_score = 0

    for tname in priority:
        if scores[tname] > best_score:
            best_score = scores[tname]
            best_type = tname

    return best_type if best_score > 0 else "Animal"
