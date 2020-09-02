# K8s prometheus custom exporter

I started to write this (long missing) exporter which provides custom metrics for:<br>
<br>

```
INGRESS_DUPLICATES - points on ingresses which are presented more than once, with path included.
EXPIRED_DOCKER_IMAGES - checks docker repository if image is present on it. No auth.
MEMORY_LIMIT_CAPACITY - displays percentage of cluster limits capacity.
```

<br>
Sadly, it works only on 1.15 release, just like the python k8s library itself on the moment of writing. Considering this, it was not tested on live.
