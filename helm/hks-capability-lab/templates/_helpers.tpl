{{/* Chart name, capped and DNS-safe. */}}
{{- define "hks.name" -}}
{{- .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "hks.fullname" -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "hks.namespace" -}}
{{- .Values.namespace.name | default .Release.Namespace -}}
{{- end -}}

{{- define "hks.labels" -}}
app.kubernetes.io/name: {{ include "hks.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/part-of: hks-capability-lab
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
{{- end -}}

{{- define "hks.selectorLabels" -}}
app.kubernetes.io/name: {{ include "hks.name" . }}
hks-capability-lab/track: stable
{{- end -}}

{{- define "hks.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "hks.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}
