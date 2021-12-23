import yaml
from pathlib import Path
import os
import git
import time
import shutil
import subprocess

from time import gmtime, strftime


google_license = """
# Copyright 2021 Google LLC
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
google_license_set = set(google_license.splitlines())
all_results = {}
repo = None

def remove_tags(fn):
    ## this will remove ALL the tags in the yaml
    with open(fn,"r") as f:
        lines = f.readlines()

    with open(fn,"w") as f:
        for line in lines:
            if not line.startswith("# [") :
                f.write(line)
                # continue
            # if not line.startswith("# [END"):
                # f.write(line)
    print("REMOVED THE TAGS at " +fn)
    return

def generate_region_tag(product, twoup, oneup, fn, snippet):
    # get the specific Kubernetes resource type, if listed. 
    if 'kind' not in snippet:
        resource_type = "yaml"
    else:
        resource_type = snippet['kind'].lower()
    filename = os.path.basename(fn)
    print(twoup, oneup)
    # have the snippet name match the k8s resource name - otherwise, match to filename 
    if 'metadata' not in snippet:
        if filename.endswith('.yaml'):
        # if no metadata name, then format: <product-prefix>_<oneup>_<filename-without-extention>_<kind>
            filename = filename[:-5]
            tag = "{}_{}_{}_{}_{}".format(product, twoup,oneup, filename ,resource_type)
        ## if the file is a shell 
        elif filename.endswith('.yml'):
            filename = filename[:-4]
            tag = "{}_{}_{}_{}_{}".format(product, twoup,oneup, filename ,resource_type)
    else: 
        if filename.endswith('.yaml'):
            filename = filename[:-5]
            metadataName = snippet['metadata']['name'].lower()
            tag = "{}_{}_{}_{}_{}".format(product, oneup, filename, resource_type,metadataName)
        elif filename.endswith('.yml'):
            filename = filename[:-4]
            metadataName = snippet['metadata']['name'].lower()
            tag = "{}_{}_{}_{}_{}".format(product, oneup, filename ,resource_type,metadataName)
    tag = tag.replace("-", "_")
    return tag

def generate_shell_tag(product, twoup,fn):
    filename = os.path.basename(fn)
    filename = filename[:-3]
    tag = "{}_{}_{}".format(product, twoup, filename )
    tag = tag.replace("-", "_")
    return tag

def process_file(product, twoup, oneup, fn):
    if oneup=="templates":
        return 
    global all_results

    yaml_comments = {}
    with open(fn) as file:
        # do not process helm charts
        results = {}
        original_contents = file.readlines()
        # print(original_contents[:14], google_license.splitlines())
        # stripped = [s.strip() for s in original_contents[:14]]
        # print(stripped==google_license.splitlines())

        if len(original_contents)<14 or original_contents[0].find('apiVersion')>=0:
            start = 0
            end = 0
        else:
            # start and end of the license if present
            start = 0
            end = 12
            # print(original_contents[end].strip()!= "# limitations under the License.")
            if original_contents[end].strip()!= "# limitations under the License.":
                start = 1
                end = 13

        ## this is so janky, but the idea is to find the comments (not including license), save comment and line location, add the length of the google license and hope it works
        yaml_sections_count = 0
        for i,line in enumerate(original_contents[end+1:]):
            check_line = line.lstrip() # remove whitespace from left of the string
            if  len(check_line)>1 and check_line[0]=='#':

                # print(i, end, yaml_sections_count, line)
                if end>0:
                    yaml_comments[i + 15 + (yaml_sections_count*3)] = line
                else:
                    yaml_comments[27 + 15 + (yaml_sections_count*3)] = line

            if line.find("kind:")>=0 and end == 0:
                yaml_sections_count+=1
                continue
            if line.find("kind:")>=0 and i>17: # skip over the first one
                print(line.find("kind:"))
                yaml_sections_count += 1

            
        print(yaml_comments)
        file.seek(0)
        documents = yaml.load_all(file, Loader=yaml.FullLoader)
        for snippet in documents:
            if snippet is None:
                continue
            tag = generate_region_tag(product, twoup, oneup, fn, snippet)
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
    with open(fn, 'w+') as output:
        output.write(google_license + "\n")
        for tag, snippet in results.items():
            start = "# [START {}]".format(tag)
            end = "# [END {}]".format(tag)
            output.write(start + "\n")
            yaml.dump(snippet, output, sort_keys=False)
            output.write(end + "\n")
            output.write("---\n")
    output.close()
    ## looping through the new file, and adding comments back in 
    # safely read then write to the file
    with open(fn,'r') as no_comments:
        buf = no_comments.readlines()
    no_comments.close() 

    # print(buf)
    # print(yaml_comments)

    for i, line in yaml_comments.items():
        buf.insert(i,line)

    with open(fn,'w') as outfile:
        buf = "".join(buf)
        outfile.write(buf)
    outfile.close()

def process_file_shell(product, oneup, fn):
    global all_results

    tag = generate_shell_tag(product,oneup,fn)
    start = "# [START {}]".format(tag)
    end = "# [END {}]".format(tag)
    insert_start = False

    with open(fn) as f:
        filIn = f.readlines()
        for i,line in enumerate(filIn):
            if line == "# limitations under the License.":
                insert_start = True
                break
        if insert_start:
            filIn.insert(i, start+ "\n")
        f.close()
    
    if insert_start == False:
        # if the file has no license, add license, add tags, add existing content, add end tag
        with open(fn) as file:
            contents = file.read()
        with open(fn,'w') as file:
            file.write(google_license + "\n")
            file.write(start + "\n")
            file.write(contents + "\n")
            file.write(end)
        file.close()
    else:
        with open(fn, 'a') as file:
            file.write(end)
        file.close()



def clone_repo(id_rsa, known_hosts, github_repository, branch, local_path):
    global repo

    # prep to clone
    my_env = os.environ.copy()
    my_env["SSH_PRIVATE_KEY"] = id_rsa
    my_env["KNOWN_HOSTS"] = known_hosts
    dir_path = os.path.dirname(os.path.realpath(__file__))
    cmd = '{}/clone_prep.sh'.format(dir_path)
    a = subprocess.run(cmd, stdout=subprocess.PIPE, env=my_env)
    print(a.stdout.decode('utf-8'))

    # clone
    repo_clone_url = 'git@github.com:{}.git'.format(github_repository)
    repo = git.Repo.clone_from(repo_clone_url, local_path)
    repo.git.checkout(branch)

def push_to_repo(local_path, branch):
    global repo
    dt = strftime("%m/%d/%Y %h:%M:%S", gmtime())
    dir_path = os.path.dirname(os.path.realpath(__file__))

    my_env = os.environ.copy()
    my_env["LOCAL_PATH"] = local_path
    my_env["BRANCH"] = branch
    my_env["COMMIT_MESSAGE"] = '[bot] generate YAML region tags {}'.format(dt)
    cmd = '{}/push.sh'.format(dir_path)

    # use script to push to github, as yamlbot
    # (no error catching / logs when doing this in python)
    a = subprocess.run(cmd, stdout=subprocess.PIPE, env=my_env)
    print(a.stdout.decode('utf-8'))


def get_repo():
    ## get reference to the repo, and create a local_branch named yaml_tags
    input_link = input('Please input the github repo github link if you do not have it cloned, or the path if its local:')
    # clone the repo if it doesn't exist already
    if input_link[:5]=="https":
        repo_directory = "/"
        repo = git.clone(input_link)
        repo.git.checkout('test')

    else:   ## else refer to a local one
        repo = git.Repo(input_link)
        repo_directory = input_link
    yaml_branch = repo.create_head("yaml_tags_comments")
    repo.head.reference = yaml_branch
    print(repo.head.reference)
    return repo, repo_directory

def log_results():
    global all_results
    # print(all_results)
    print("✅ success: total resources processed: {}".format(len(all_results.keys())))

if __name__ == "__main__":

    env_file = input("0: env file, or 1:existing clone of the repo local, or 'REMOVE_TAGS' to remove all the tags from sh and yaml: ")
    
    if env_file=='0':
        id_rsa = os.environ['ID_RSA']
        if id_rsa == "":
            print("Error: ID_RSA env variable must be set")
            exit(1)

        known_hosts = os.environ['KNOWN_HOSTS']
        if known_hosts == "":
            print("Error: KNOWN_HOSTS env variable must be set")
            exit(1)

        product = os.environ['PRODUCT']
        if product == "":
            print("Error: PRODUCT env variable must be set")
            exit(1)


        github_repo_name = os.environ['GITHUB_REPOSITORY']
        if github_repo_name == "":
            print("Error: GITHUB_REPOSITORY env variable must be set.")
            exit(1)

        branch = os.environ['GITHUB_REF']
        if branch == "":
            print("Error: GITHUB_REF env variable must be set.")
            exit(1)

        # clone repo
        local_path = "/tmp/{}".format(github_repo_name)
        shutil.rmtree(local_path, ignore_errors=True)
        clone_repo(id_rsa, known_hosts, github_repo_name, branch, local_path)

        # prepare to process snippets
        path = Path(local_path)

        for p in path.rglob("*.yaml"):
            filename = p.name
            fullparent = str(p.parent)
            fn = fullparent +  "/" + filename
            print("processing: {}".format(fn))
            spl = fullparent.split("/")
            oneup = spl[-1]
            twoup = spl[-2]
            process_file(product, twoup, oneup, fn)

        push_to_repo(local_path, branch)
        log_results()

    elif env_file == '1':
        directory, local_path = get_repo()
        # prod_prefix = input("Input the product prefix:")
        prod_prefix = 'anthosconfig'

        path = Path(local_path)
        print("PROCESSING YAML")
        # fn = '/Users/christineskim/Documents/repos/anthos-service-mesh-samples/docs/security/update-authentication-policies/security_auth_policy.yaml'
        # oneup = 'update-authentication-policies'
        # twoup = 'security'
        # fn = '/Users/christineskim/Documents/repos/anthos-service-mesh-samples/demos/bank-of-anthos-asm-manifests/demo-manifests/frontend-custom-deployment.yml'
        # oneup = 'demo-manifests'
        # twoup = 'bank-of-anthos-asm-manifests'
        # fn = '/Users/christineskim/Documents/repos/anthos-service-mesh-samples/docs/mtls-egress-ingress/server/mysql-server/mysql.yaml'
        # oneup = 'mysql-server'
        # twoup = 'server'
        # process_file(prod_prefix, twoup, oneup, fn)
        for p in path.rglob("*.yaml"):
            filename = p.name
            fullparent = str(p.parent)
            fn = fullparent +  "/" + filename
            print("processing: {}".format(fn))
            spl = fullparent.split("/")
            oneup = spl[-1]
            twoup = spl[-2]
            # print(twoup,oneup)
            process_file(prod_prefix, twoup, oneup, fn)
            
        for p in path.rglob("*.yml"):
            filename = p.name
            fullparent = str(p.parent)
            fn = fullparent +  "/" + filename
            print("processing: {}".format(fn))
            spl = fullparent.split("/")
            oneup = spl[-1]
            twoup = spl[-2]
            process_file(prod_prefix, twoup, oneup, fn)

        # capturing shell scripts to tag

        print("PROCESSING SHELL")
        for p in path.rglob("*.sh"):
            filename = p.name
            fullparent = str(p.parent)
            fn = fullparent +  "/" + filename
            print("processing: {}".format(fn))
            spl = fullparent.split("/")
            oneup = spl[-1]
            twoup = spl[-2]
            # print("===================",twoup,oneup)
            process_file_shell(prod_prefix, oneup,fn)
        branch='yaml_tags'
        # push_to_repo(local_path, branch)
        log_results()
    elif env_file =="REMOVE_TAGS":
        print("************** REMOVING TAGS")
        directory, local_path = get_repo()
        path = Path(local_path)
        for p in path.rglob("*.yaml"):
            filename = p.name
            fullparent = str(p.parent)
            fn = fullparent +  "/" + filename
            remove_tags(fn)

        for p in path.rglob("*.yml"):
            filename = p.name
            fullparent = str(p.parent)
            fn = fullparent +  "/" + filename
            remove_tags(fn)