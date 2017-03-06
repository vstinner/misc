/*
 * Short program to test locale conversions.
 *
 * Compile it with:
 *    gcc -std=c99 locale.c -o locale
 *
 * It requires ISO C99 for L"\uHHHH" and L"\UHHHHHHHH".
 */

#ifdef _MSC_VER
#  define MS_WINDOWS
#endif

#include <ctype.h>
#include <wctype.h>
#include <locale.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <string.h>
#ifndef MS_WINDOWS
#include <langinfo.h>
#endif

#define ARRAY_SIZE(array) (sizeof(array) / sizeof(array[0]))

#define YES_NO(cond) ((cond)?"yes":"no")

static void
dump_char_string(FILE *f, const char *prefix, const char *string, const char *suffix)
{
    unsigned c;
    fputs(prefix, f);
    for (; *string != L'\0'; string++) {
        c = (unsigned char)*string;
        if (c < 128)
            fputc((char)c, f);
        else
            fprintf(f, "\\x%02x", c);
    }
    fputs(suffix, f);
    fflush(f);
}

static void
dump_wchar_string(FILE *f, char *prefix, const wchar_t *string, char *suffix)
{
    unsigned long c;
    fputs(prefix, f);
    for (; *string != L'\0'; string++) {
        c = (unsigned long)*string;
        if (c < 128)
            fputc((char)c, f);
        else if (c < 256)
            fprintf(f, "\\x%02x", (unsigned int)c);
        else if (c < 65536)
            fprintf(f, "\\u%04x", (unsigned int)c);
        else
            fprintf(f, "\\U%08x", (unsigned int)c);
    }
    fputs(suffix, f);
    fflush(f);
}

void to_wchar(const char *bytes)
{
    wchar_t buffer[100];
    size_t res;

    memset(buffer, 0xaa, sizeof(buffer));

    dump_char_string(stdout, "char* {", bytes, "} => ");
    res = mbstowcs(buffer, bytes, ARRAY_SIZE(buffer) - 1);
    buffer[ARRAY_SIZE(buffer)-1] = 0;
    if (res != (size_t)-1) {
        /* mbstowcs() is supposed to write a null character, just be extra
           safe */
        buffer[res] = L'\0';
        dump_wchar_string(stdout, "wchar_t* {", buffer, "}\n");
    } else
        fprintf(stdout, "mbstowcs() error\n");
}

void to_bytes(const wchar_t *text)
{
    char buffer[100];
    size_t res;

    memset(buffer, 0xaa, sizeof(buffer));

    dump_wchar_string(stdout, "wchar_t* {", text, "} => ");
    res = wcstombs(buffer, text, ARRAY_SIZE(buffer) - 1);
    buffer[ARRAY_SIZE(buffer)-1] = 0;
    if (res != (size_t)-1)
        dump_char_string(stdout, "char* {", buffer, "}\n");
    else
        fprintf(stdout, "wcstombs() error\n");
}

void dump_locale(const char *name, int category)
{
    char *value;
    value = setlocale(category, NULL);
    printf("%s = %s\n", name, value);
#if !defined(MS_WINDOWS) && defined(CODESET)
    printf("nl_langinfo(CODESET) = %s\n", nl_langinfo(CODESET));
#endif
}

void byte_is_letter(unsigned char ch)
{
    printf("0x%02x is a letter? %s\n",
           (unsigned char)ch, YES_NO(isalpha(ch)));
}

void char_is_letter(wchar_t ch)
{
    printf("U+0x%04x is a letter? %s\n",
           ch, YES_NO(iswalpha(ch)));
}

int main()
{
    setlocale(LC_CTYPE, "");
    dump_locale("LC_CTYPE", LC_CTYPE);
    printf("wchar_t: %u bits\n", (unsigned int)sizeof(wchar_t) * 8);
    printf("\n");

    byte_is_letter('a');
    byte_is_letter(0x80);
    byte_is_letter(0xe9);
    char_is_letter(L'a');
    char_is_letter(L'\xe9');
    char_is_letter(L'\u20ac');
    printf("\n");

    to_wchar("abc");
    to_wchar("0xff:\xff");
    to_wchar("0xe9:\xe9");
    to_wchar("0xc3 0xa9:\xc3\xa9");
    to_wchar("euro:\xa4");
    printf("\n");

    to_bytes(L"abc");
    to_bytes(L"\xe9");

    /* \u requires ISO C99 */
    to_bytes(L"\u20ac");

    /* \U require ISO C99 and 32 bits wchar_t */
    to_bytes(L"\U0010ffff");

    return 0;
}
