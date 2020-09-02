from prometheus_client import start_http_server, Summary, Gauge
from kubernetes import client, config
from collections import defaultdict
import collections
import docker
import time

config.load_kube_config()
v1beta = client.ExtensionsV1beta1Api()
v1core = client.CoreV1Api()
docker_client = docker.from_env()

INGRESS_DUPLICATES = Gauge('ingress_duplicates', 'Ingresses which are dublicated on the same cluster', ['ingress'])
EXPIRED_DOCKER_IMAGES = Gauge('docker_images_expired', 'Images which are not present in docker registry', ['image'])
MEMORY_LIMIT_CAPACITY = Gauge('memory_limit_capcity', 'Percentage ratio of limits and allocatable memory', ['node'])


def IngressDuplicates():
  ingresses_all = v1beta.list_ingress_for_all_namespaces(watch=False)
  ingress_duplicates = []
  for ing in ingresses_all.items:
     for rule in ing.spec.rules:
       for path in rule.http.paths:
         if (rule.host is not None):
            ingress_duplicates.append(rule.host + path.path)
  list_of_duplicatess = ([item for item, count in collections.Counter(ingress_duplicates).items() if count > 1])
  for i in list_of_duplicatess:
    INGRESS_DUPLICATES.labels(i).set(1)


def PodMemoryLimitsCapacity():
  for node in v1core.list_node().items:
     node_name = node.metadata.name
     allocatable = node.status.allocatable
     stats = {}
     stats["mem_alloc"] = int(allocatable["memory"].replace('Ki','')) / 1024
     selector = ( "status.phase!=Succeeded,status.phase!=Failed," + "spec.nodeName=" + node_name)
     #ensure all pods are listed
     max_pods = int(int(allocatable["pods"]) * 1.5)
     pods = v1core.list_pod_for_all_namespaces(field_selector=selector, limit=max_pods)
     memoryreqs = []
     for pod in pods.items:
       for container in pod.spec.containers:
         #need to populate data even if there is no data at all
          request = defaultdict(lambda: 0, container.resources.requests or {})
          request_memory = request['memory']
          #need to convert all ki\mi to plain numbers
          if type(request_memory) is str:
             if ("Mi" in request_memory):
               request_memory = str(request_memory.replace('Mi',''))
             if ("Gi" in request_memory):
               request_memory = str(int(request_memory.replace('Gi','')) * 1024)
          memoryreqs.append(int(request_memory))
     stats["mem_req"] = sum(memoryreqs)
     capacity = int(stats["mem_req"] / stats["mem_alloc"] * 100)
     MEMORY_LIMIT_CAPACITY.labels(node_name).set(capacity)

def DockerImageExpiration():
  deployed_images = []
  pods = v1core.list_pod_for_all_namespaces()
  for pod in pods.items:
    for container in pod.spec.containers:
      deployed_images.append(container.image)
  #convert list to set to get uniquie images
  for image in set(deployed_images):
   try:
    image_attrs = docker_client.images.get_registry_data(image, auth_config=None)
   except:
     EXPIRED_DOCKER_IMAGES.labels(image).set(1)
  
if name == '__main__':
    start_http_server(9999)
    while True:
        PodMemoryLimitsCapacity()
        IngressDuplicates()
        DockerImageExpiration()
        time.sleep(1000)
