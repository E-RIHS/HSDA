#! /usr/bin/env python3

import requests
import json


BASE_API_URL = "https://vocab.e-rihs.io/opentheso2/openapi/v1/concept/handle/"
RESOLVED_URL = "https://hdl.handle.net/"
TOP_LEVEL_HDL = "21.11158/0001-4b3x8990cw9fkpcw7dt4hx43x"


def fetch_concept(hdl):
    response = requests.get(BASE_API_URL + hdl)
    response.raise_for_status()
    data = response.json()
    full_handle = RESOLVED_URL + hdl
    return data[full_handle]


def get_list_of_narrower_concepts(concept):

    if not concept["http://www.w3.org/2004/02/skos/core#narrower"]:
        return []
    
    narrower_concepts = []
    for item in concept["http://www.w3.org/2004/02/skos/core#narrower"]:
        narrower_concepts.append(item["value"].replace(RESOLVED_URL, ""))

    return narrower_concepts


def main():
    # get top level concept
    top_level_concept = fetch_concept(TOP_LEVEL_HDL) 
    
    # get all narrower concepts, recursively, and push them to cordra
    children = get_list_of_narrower_concepts(top_level_concept)
    for child in children:
        print(child)


if __name__ == "__main__":
    main()