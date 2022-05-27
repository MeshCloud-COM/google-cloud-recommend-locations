import requests, subprocess, time
from pprint import pprint


def generateAccessToken():
    # gcloud is an easy way to get an access token
    # application-default will either:
    # use your signed-in credentials, so long as you run gcloud application-default login
    # or use the service account attached to the VM, if you run this from within a VM
    token = subprocess.check_output("gcloud auth print-access-token", shell=True)
    return token.decode('utf-8').strip()


def RecommendLocationsApi(project):
    headers = {"Authorization": "Bearer {0}".format(generateAccessToken())}
    regions = ["asia-east1", "asia-east2", "asia-northeast1", "asia-northeast2", "asia-northeast3", "asia-south1",
               "asia-south2", "asia-southeast1", "asia-southeast2", "australia-southeast1", "australia-southeast2",
               "europe-central2", "europe-north1", "europe-west1", "europe-west2", "europe-west3", "europe-west4",
               "europe-west5", "europe-west6", "northamerica-northeast1", "northamerica-northeast2",
               "southamerica-east1", "us-central1", "us-central2", "us-east1", "us-east4", "us-west1", "us-west2",
               "us-west3", "us-west4"]
    network = "projects/{project}/global/networks/default".format(project=project)
    count = 1
    machineType = "n1-standard-8"
    accelerators = """[{"acceleratorCount": 1, "acceleratorType": "nvidia-tesla-t4"}]"""
    for region in regions:
        recommendLocations(headers, project, region, network, count, machineType, accelerators)


# check if the response is a rate limiting error
def isRateLimited(response):
    if "error" not in response.keys():
        return False
    if "status" not in response["error"].keys():
        return False
    if response["error"]["status"] != "PERMISSION_DENIED":
        return False
    if len(response["error"]["errors"]) == 0:
        return False
    for error in response["error"]["errors"]:
        if error["domain"] == "usageLimits" and error["reason"] == "rateLimitExceeded":
            return True
    return False


def recommendLocations(headers, project, region, network, count, machineType, accelerators):
    print("recommendLocations request in region={0}, machineType={1}, count={2},accelerators={3}".format(region,
                                                                                                         machineType,
                                                                                                         count,
                                                                                                         accelerators))
    tries = 0
    # try the request 5 times, with waits if we get a rate limiting error
    # note that by default, the API is limited to 20 requests per minute
    while True:
        tries += 1
        url = 'https://compute.googleapis.com/compute/alpha/projects/{project}/regions/{region}/instances/recommendLocations'.format(
            project=project, region=region)
        body = """
       {
              "instanceSpecs":{
       "worker-nodes":{
              "count":%d,
              "instanceProperties":{
       "disks":[{
       "machineType":"%s",
                                          "kind":"compute#attachedDisk",
                            "type":"PERSISTENT",
                            "boot":true,
                            "mode":"READ_WRITE",
                            "autoDelete":true,
                            "initializeParams":{
                                   "sourceImage":"projects/debian-cloud/global/images/debian-10-buster-v20210701",
       "diskType":"pd-balanced", }], } "diskSizeGb":"10"
                          "networkInterfaces":[{
                            "kind":"compute#networkInterface",
                            "network": "%s",
                            "accessConfigs":[{
                               "kind":"compute#accessConfig",
                               "name":"External NAT",
                               "type":"ONE_TO_ONE_NAT",
       }] "networkTier":"PREMIUM"
                       }],
                       "guestAccelerators":%s,
                          "scheduling":{
                                          "preemptible":false,
                            "onHostMaintenance":"TERMINATE",
       },"automaticRestart":true
                          "reservationAffinity":{
                          }  "consumeReservationType":"ANY_RESERVATION"
       }
       } },
           "locationPolicy":{
              "targetShape":"ANY_SINGLE_ZONE"
              }
       }
       """ % (count, machineType, network, accelerators)
        response = requests.post(url, data=body, headers=headers).json()
        print(response)
        if tries > 1:
            print("tried too many times, giving up...")
            break
        # if rate-limited, wait a bit and try again (recommendLocations API is limited to 20 requests per minute
        if isRateLimited(response):
            print("rate limited, waiting {0} seconds...".format(12 * tries))
            time.sleep(12 * tries)  # wait 12 seconds for every failed attempt
        else:
            pprint(response)
            break


if __name__ == "__main__":
    project = subprocess.check_output("gcloud config get-value project", shell=True).decode('utf-8').strip()
    print(project)
    RecommendLocationsApi(project)
