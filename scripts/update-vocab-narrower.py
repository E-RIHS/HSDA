#! /usr/bin/env python3

'''
This script fetches all ids of the vocabulary concepts in a Cordra instance
and subsequentially calles the type method updateObjectWithNarrower type method 
on each of them.
'''

import os
import sys
import time

from libcordra import Cordra


CORDRA_API_URL = "https://data.e-rihs.io/"
CORDRA_TYPE = "VocabularyConcept"
SLEEP_TIME = 0.5


def load_env_files() -> None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    for base in (root_dir, script_dir):
        env_path = os.path.join(base, ".env")
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            key, val = line.split("=", 1)
                            key = key.strip()
                            val = val.strip().strip('"').strip("'")
                            if key and key not in os.environ:
                                os.environ[key] = val
            except Exception:
                pass


def main():
    load_env_files()
    cordra_user = os.getenv("CORDRA_USER")
    cordra_passwd = os.getenv("CORDRA_PASSWD")
    if not cordra_user or not cordra_passwd:
        print("\033[91mMissing CORDRA_USER or CORDRA_PASSWD in environment/.env\033[0m")
        sys.exit(1)

    cordra = Cordra(CORDRA_API_URL, cordra_user, cordra_passwd)

    # fetch all ids of the vocabulary concepts in the Cordra instance
    query = f"type:{CORDRA_TYPE}"
    response = cordra.query(query, ids=True)

    print(f"Found {len(response)} vocabulary concepts")

    # loop through the vocabulary concepts and call the type method updateObjectWithNarrower
    for concept in response:
        print(f"Updating object with id {concept}")
        cordra.call_type_method(concept, "updateObjectWithNarrower")
        # wait for 0.5 seconds to be gentle on the server
        time.sleep(SLEEP_TIME)

    print("Finished")


if __name__ == "__main__":
    main()