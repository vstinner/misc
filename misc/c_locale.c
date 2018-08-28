#include <langinfo.h>
#include <locale.h>
#include <stdio.h>
#include <stdlib.h>

int main()
{
    setlocale(LC_ALL, "C");
    printf("LC_ALL: %s\n", setlocale(LC_ALL, NULL));
    printf("LC_CTYPE: %s\n", setlocale(LC_CTYPE, NULL));
    printf("nl_langinfo(CODESET): %s\n", nl_langinfo(CODESET));
    for (unsigned i=0; i<=255; i++) {
        char bytes[2];
        wchar_t text[10];
        bytes[0] = (char)i;
        bytes[1]= '\0';
        size_t res = mbstowcs(text, bytes, 1);
        if (res != (size_t)-1) {
            printf("byte 0x%02X decoded to Unicode character U+%04X\n", (unsigned char)i, text[0]);
        }
        else {
            printf("byte 0x%02X cannot be decoded\n", (unsigned char)i);
        }
    }
    return 0;
}
