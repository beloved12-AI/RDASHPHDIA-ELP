{{- define "hybrid-opt.name" -}}
hybrid-opt
{{- end -}}

{{- define "hybrid-opt.fullname" -}}
{{ printf "%s" (include "hybrid-opt.name" .) }}
{{- end -}}
