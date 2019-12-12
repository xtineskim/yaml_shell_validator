import yaml
from pathlib import Path
import os
from git import Repo
import time


google_license = """
# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""

all_results = {}

def generate_region_tag(product, twoup, oneup, snippet):
    if 'kind' not in snippet:
        print("**** snippet " + snippet + "is invalid")
        return ""
    resource_type = snippet['kind'].lower()
    name = snippet['metadata']['name'].lower()
    tag = "{}_{}_{}_{}_{}".format(product, twoup, oneup, resource_type, name)
    tag = tag.replace("-", "_")
    return tag


def process_file(product, twoup, oneup, fn):
    global all_results
    with open(fn) as file:
        results = {}
        documents = yaml.load_all(file)
        for snippet in documents:
            if snippet is None:
                continue
            tag = generate_region_tag(product, twoup, oneup, snippet)
            # handle duplicates.
            if tag in all_results:
                print("⭐️ tag {} already in all_results, adding a #". format(tag))
                x = 2
                numbered_tag = tag + str(x)
                while numbered_tag in all_results:
                    print("tag {} already in all_results, adding a #". format(numbered_tag))
                    x = x + 1
                    numbered_tag = tag + str(x)
                print("adding numbered tag: {} to all_results \n".format(numbered_tag))
                results[numbered_tag] = snippet
                all_results[numbered_tag] = snippet
            else:
                results[tag] = snippet
                all_results[tag] = snippet

    file.close()
    # write new YAML file with google license, START and END
    with open(fn, 'w') as output:
        output.write(google_license + "\n")
        for tag, snippet in results.items():
            start = "# [START {}]".format(tag)
            end = "# [END {}]".format(tag)
            output.write(start + "\n")
            yaml.dump(snippet, output)
            output.write(end + "\n")
            output.write("---\n")
    output.close()


def log_results():
    global all_results
    print("total resources processed: {}".format(len(all_results.keys())))


if __name__ == "__main__":
    # repo_path = os.environ['REPO_PATH']
    # if repo_path == "":
    #     print("Error: REPO_PATH env variable must be set.")
    #     os.exit(1)

    # # clone git directory
    # git.Git("/tmp/").clone("git://{}.git".format(repo_path))

    # # clone repo

    # prepare to process snippets
    product = os.environ['PRODUCT']
    if product == "":
        print("Error: PRODUCT env variable must be set")
        os.exit(1)


    path = Path('/Users/mokeefe/go/src/github.com/askmeegs/istio-samples')
    # path = Path("/tmp/{}".format(repo_path))

    for p in path.rglob("*.yaml"):
        filename = p.name
        fullparent = str(p.parent)
        fn = fullparent +  "/" + filename
        print("processing: {}".format(fn))
        spl = fullparent.split("/")
        oneup = spl[-1]
        twoup = spl[-2]
        process_file(product, twoup, oneup, fn)

    log_results()

    # TODO - commit changes to repo
    # todo - handle git authentication?