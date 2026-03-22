{{- define "task-system.fullname" -}}
{{- printf "%s" .Chart.Name -}}
{{- end -}}

{{- define "task-system.apiImage" -}}
{{- printf "%s:%s" .Values.api.image.repository .Values.api.image.tag -}}
{{- end -}}

{{- define "task-system.workerImage" -}}
{{- printf "%s:%s" .Values.worker.image.repository .Values.worker.image.tag -}}
{{- end -}}

{{- define "task-system.webImage" -}}
{{- printf "%s:%s" .Values.web.image.repository .Values.web.image.tag -}}
{{- end -}}
