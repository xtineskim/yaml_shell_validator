import git
import os
import requests
import yaml


all_results = {}
repo = None
repo_directory = ""

def get_repo():
    ## get reference to the repo, and create a local_branch
    input_link = input('Please input the github repo github link if you do not have it cloned, or the path if its local:')
    # clone the repo if it doesn't exist already
    if input_link[:5]=="https":
        repo_directory = "/"
        repo = git.clone(input_link)
        repo.git.checkout('test')

    else:   ## else refer to a local one
        repo = git.Repo(input_link)
        repo_directory = input_link
    yaml_branch = repo.create_head("yaml_tags")
    repo.head.reference = yaml_branch
    print(repo.head.reference)
    return repo, repo_directory

def remove_tags():
    return True

def check_region_tag(tag,prod_prefix, dir):
    ## checks if an already existing tag is valid 

    if tag == generate_region_tag(prod_prefix,dir):
        return True
    else:
        return False


def generate_region_tag(prod_prefix,dir,filename, resource_type,snippet):
    if 'kind' not in snippet:
        resource_type = "yaml"
    else:
        resource_type = snippet['kind'].lower()

    config_name = snippet['metadata']['name'].lower()

    #REGION TAG FORMAT: YAML 
    # <product-prefix>_<directory-with-underscores>_<filename-without-extention>_<resource_type>_<name>
    tag = "{}_{}_{}_{}_{}".format(prod_prefix, dir,filename,resource_type, config_name)
    tag = tag.replace("-", "_")
    return tag

def validate_file(product, twoup,oneup, fn):
    if oneup=="templates":
        return 
    global all_results
    with open(fn) as file:
        # do not process helm charts
        results = {}
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

if __name__=="__main__":
    directory, local_path = get_repo()
    # prod_prefix = input("what is the product prefix?")
    prod_prefix = 'servicemesh'

    with open('/Users/christineskim/Documents/repos/microservices-demo/skaffold.yaml') as f:
        t = yaml.safe_load_all(f)
        for data in t:
            for k,v in data.items():
                print(k, '      ', v)
            print("\n")


    for subdir,dirs,files in os.walk(local_path):
        for file in files:
            if file[-5:]=='.yaml':
                print('yaml file')

                fn = os.path.join(subdir,file)
                print(os.path.join(subdir,file), os.path.basename(subdir))
                

                validate_file(prod_prefix,twoup,oneup,fn)
                # tag = generate_region_tag(prod_prefix,subdir, file)
            elif file[-3] =='.sh':
                print('Shell file')







    
