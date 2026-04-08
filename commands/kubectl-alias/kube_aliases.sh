# --- Namespace Management ---
alias kns='echo $KNS'

kdev(){
  export KNS="-nibus-cloud-eng"
  echo "Switched to namespace: ibus-cloud-eng"
}

kprod(){
  export KNS="-nibus-cloud-prod"
  echo "Switched to namespace: ibus-cloud-prod"
}

kall(){
  export KNS="--all-namespaces"
  echo "Switched to ALL namespaces"
}

# --- kubectl Wrapper ---
k(){
  kubectl "$@"
}

kubectl(){
  if [[ $# -eq 0 ]]; then
    command kubectl
    return
  fi

  cmd="$1"
  shift
  command kubectl "$cmd" "${KNS:+$KNS}" "$@"
}

# --- Common kubectl Aliases ---
alias kpods='kubectl get pods | grep'
alias kpod='kubectl get pods'
alias klogs='kubectl logs'
alias klogf='kubectl logs -f'
alias klogh='kubectl logs --since=1h'
alias kdes='kubectl describe pod'
alias kwide='kubectl get pods -o wide | grep'
alias ksvc='kubectl get svc'
alias kdeploy='kubectl get deployments'
alias kin='kubectl get ingress'
alias kbroken='kubectl get pods | grep -iE "backoff|error|evicted|unknown"'

# --- Utility: Pretty logs ---
kute() {
  sed 's/\\n/\
/g' "$@"
}

# --- JWT Decode using local Python script ---
#jwt(){
#  python3 ~/Github/Scripts/python/jwtDecode/jwtDecode.py "$1"
#}

# --- Heapdump Copy ---
kdump(){
  local pod="$1"
  local base_name
  base_name=$(echo "$pod" | sed 's/-.*//')
  kubectl cp "$pod":/mnt/mesos/sandbox/. ~/heapdump/"$base_name"$(date +"%Y%m%d").hprof
}

# --- List dump directory inside pod ---
kldump(){
  kubectl exec "$1" -- ls -lsat /mnt/mesos/sandbox
}

# --- Exec into pod ---
kexec(){
  kubectl exec -it "$1" bash
}

# --- Extract image name from pod ---
kimg(){
  if [ $# -gt 1 ]; then
    for pod in "$@"; do
      echo "$pod" | sed 's/-[^-]*//2g'
      kubectl describe pod "$pod" | grep Image: | sed 's/.*://' | tail -n1
      echo ""
    done
  else
    kubectl describe pod "$1" | grep Image: | sed 's/.*://' | tail -n1
  fi
}

# --- Show node info for pod ---
khost(){
  if [ $# -gt 1 ]; then
    for pod in "$@"; do
      echo "$pod"
      kubectl describe pod "$pod" | grep Node:
      echo ""
    done
  else
    kubectl describe pod "$1" | grep Node:
  fi
}
