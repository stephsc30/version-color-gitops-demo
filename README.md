# Version Color GitOps Demo

This project demonstrates Argo Rollouts canary and blue-green deployments using Helm, Istio Gateway API, and a NodePort gateway.

It intentionally starts without Argo CD so you can understand Rollouts first. Later, replace `helm upgrade` with Git commits and Argo CD sync.

## Structure

```text
version-color-gitops-demo/
  app/
    server.py
    Dockerfile
    .dockerignore
  chart/
    Chart.yaml
    values.yaml
    values-canary.yaml
    values-bluegreen.yaml
    templates/
      services.yaml
      rollout.yaml
      httproute.yaml
  platform/
    nodeport-gateway.yaml
    argo-rollouts-gatewayapi-plugin.yaml
  argocd/
    application-canary.yaml
    application-bluegreen.yaml
```

## Prerequisites

- Kubernetes cluster on AWS VMs
- `kubectl`
- `helm`
- `istioctl`
- `docker`
- AWS security group allowing TCP `30080` from your laptop/VPN IP

## Install Platform Components

Install Gateway API CRDs:

```sh
kubectl get crd gateways.gateway.networking.k8s.io || \
kubectl kustomize "github.com/kubernetes-sigs/gateway-api/config/crd?ref=v1.5.1" | kubectl apply -f -
```

Install Istio minimal:

```sh
istioctl install --set profile=minimal -y
```

Install Argo Rollouts:

```sh
kubectl create namespace argo-rollouts
kubectl apply -n argo-rollouts -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml
```

Install Gateway API traffic router plugin:

```sh
kubectl apply -f platform/argo-rollouts-gatewayapi-plugin.yaml
kubectl rollout restart deployment argo-rollouts -n argo-rollouts
kubectl rollout status deployment argo-rollouts -n argo-rollouts
```

Create the Istio Gateway exposed with NodePort:

```sh
kubectl apply -f platform/nodeport-gateway.yaml
kubectl get gateway -n istio-gateway
kubectl get svc -n istio-gateway
```

The gateway should expose:

```text
NODE_IP:30080
```

## Build And Push Images

Replace `YOUR_DOCKERHUB_USER` with your Docker Hub username.

```sh
docker login

docker build -t YOUR_DOCKERHUB_USER/version-color-demo:v1 ./app
docker push YOUR_DOCKERHUB_USER/version-color-demo:v1

docker build -t YOUR_DOCKERHUB_USER/version-color-demo:v2 ./app
docker push YOUR_DOCKERHUB_USER/version-color-demo:v2

docker build -t YOUR_DOCKERHUB_USER/version-color-demo:v3 ./app
docker push YOUR_DOCKERHUB_USER/version-color-demo:v3
```

## Run Canary And Blue-Green Together

Both releases can run in the same namespace because all resources use the Helm release name.

Install canary v1:

```sh
helm upgrade --install version-color-canary ./chart \
  -n gitops-demo \
  --create-namespace \
  -f chart/values.yaml \
  -f chart/values-canary.yaml \
  --set image.repository=YOUR_DOCKERHUB_USER/version-color-demo \
  --set image.tag=v1
```

Install blue-green v1:

```sh
helm upgrade --install version-color-bluegreen ./chart \
  -n gitops-demo \
  --create-namespace \
  -f chart/values.yaml \
  -f chart/values-bluegreen.yaml \
  --set image.repository=YOUR_DOCKERHUB_USER/version-color-demo \
  --set image.tag=v1
```

Test:

```text
http://NODE_IP:30080/canary
http://NODE_IP:30080/bluegreen/active
http://NODE_IP:30080/bluegreen/preview
```

## Canary Upgrade

Upgrade canary from v1 to v2:

```sh
helm upgrade version-color-canary ./chart \
  -n gitops-demo \
  -f chart/values.yaml \
  -f chart/values-canary.yaml \
  --set image.repository=YOUR_DOCKERHUB_USER/version-color-demo \
  --set image.tag=v2
```

Watch:

```sh
kubectl argo rollouts get rollout version-color-canary -n gitops-demo --watch
kubectl get httproute version-color-canary-route -n gitops-demo -o yaml
```

Refresh:

```text
http://NODE_IP:30080/canary
```

During rollout you should see v1 and v2. The HTTPRoute weights move gradually.

## Blue-Green Upgrade

Upgrade blue-green from v1 to v2:

```sh
helm upgrade version-color-bluegreen ./chart \
  -n gitops-demo \
  -f chart/values.yaml \
  -f chart/values-bluegreen.yaml \
  --set image.repository=YOUR_DOCKERHUB_USER/version-color-demo \
  --set image.tag=v2
```

Before promotion:

```text
http://NODE_IP:30080/bluegreen/active   -> v1
http://NODE_IP:30080/bluegreen/preview  -> v2
```

Promote:

```sh
kubectl argo rollouts promote version-color-bluegreen -n gitops-demo
```

After promotion:

```text
http://NODE_IP:30080/bluegreen/active -> v2
```

## Useful Checks

```sh
kubectl get pods -n gitops-demo
kubectl get rollout -n gitops-demo
kubectl get svc -n gitops-demo
kubectl get httproute -n gitops-demo
kubectl describe rollout version-color-canary -n gitops-demo
kubectl describe rollout version-color-bluegreen -n gitops-demo
```

## Important Mental Model

Manual Rollouts mode:

```text
helm upgrade --set image.tag=v2
```

GitOps mode later:

```text
edit values.yaml -> git commit -> git push -> Argo CD sync
```

Everything else stays the same.

## Argo CD GitOps Mode

Use this after the manual Helm demo works.

Install Argo CD:

```sh
kubectl create namespace argocd
kubectl apply -n argocd --server-side --force-conflicts -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl get pods -n argocd
```

Access the Argo CD UI safely with port-forward:

```sh
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

Open:

```text
https://localhost:8080
```

Username:

```text
admin
```

Get the initial password:

```sh
kubectl get secret argocd-initial-admin-secret -n argocd -o jsonpath="{.data.password}" | base64 -d
```

Before applying the Argo CD Applications, edit both files and set your real GitHub repo URL:

```text
argocd/application-canary.yaml
argocd/application-bluegreen.yaml
```

Replace:

```text
https://github.com/YOUR_GITHUB_USER/version-color-gitops-demo.git
```

Also make sure these files contain your real image repository:

```text
chart/values-gitops-canary.yaml
chart/values-gitops-bluegreen.yaml
```

Commit and push the repo:

```sh
git add .
git commit -m "add argo cd gitops rollout demo"
git push
```

Apply both Argo CD Applications:

```sh
kubectl apply -f argocd/application-canary.yaml
kubectl apply -f argocd/application-bluegreen.yaml
```

Check Argo CD:

```sh
kubectl get applications -n argocd
```

Check deployed workloads:

```sh
kubectl get rollout -n gitops-demo
kubectl get pods -n gitops-demo
kubectl get httproute -n gitops-demo
```

Test:

```text
http://NODE_IP:30080/canary
http://NODE_IP:30080/bluegreen/active
http://NODE_IP:30080/bluegreen/preview
```

### GitOps Canary Release

Build and push the next image first:

```sh
docker build -t stephsc30/version-color-demo:v2 ./app
docker push stephsc30/version-color-demo:v2
```

Then edit only:

```text
chart/values-gitops-canary.yaml
```

Change:

```yaml
image:
  tag: v2
```

Commit and push:

```sh
git add chart/values-gitops-canary.yaml
git commit -m "release canary v2"
git push
```

Argo CD syncs the Helm chart, then Argo Rollouts performs the canary.

Watch:

```sh
kubectl argo rollouts get rollout version-color-canary -n gitops-demo --watch
kubectl get httproute version-color-canary-route -n gitops-demo -o yaml
```

### GitOps Blue-Green Release

Build and push the next image first:

```sh
docker build -t stephsc30/version-color-demo:v2 ./app
docker push stephsc30/version-color-demo:v2
```

Then edit only:

```text
chart/values-gitops-bluegreen.yaml
```

Change:

```yaml
image:
  tag: v2
```

Commit and push:

```sh
git add chart/values-gitops-bluegreen.yaml
git commit -m "release bluegreen v2"
git push
```

Before promotion:

```text
http://NODE_IP:30080/bluegreen/active   -> old version
http://NODE_IP:30080/bluegreen/preview  -> new version
```

Promote:

```sh
kubectl argo rollouts promote version-color-bluegreen -n gitops-demo
```

After promotion:

```text
http://NODE_IP:30080/bluegreen/active -> new version
```

### GitOps Mental Model

Manual mode:

```text
helm upgrade ... --set image.tag=v2
```

Argo CD mode:

```text
edit values-gitops-*.yaml -> git commit -> git push
```

Argo CD reads Git and applies Helm. Argo Rollouts still controls the canary and blue-green behavior.
