package observability

import (
	"log"
	"os"
)

type Logger struct {
	*log.Logger
}

func New(serviceName string) Logger {
	return Logger{Logger: log.New(os.Stdout, serviceName+" ", log.LstdFlags|log.LUTC)}
}
