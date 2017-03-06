CC=gcc
CFLAGS=-Wall -Wextra -Werror

all: locale libnobuffer.so

locale: locale.c
	$(CC) $< -std=c99 $(CFLAGS) -o $@

libnobuffer.so: nobuffer.c
	$(CC) -shared nobuffer.c $(CFLAGS) -fPIC -o $@

clean:
	rm -f locale libnobuffer.so

