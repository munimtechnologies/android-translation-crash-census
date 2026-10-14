// Licensed under the Apache License, Version 2.0 (Apache-2.0).
// Made by MV2 of Munim, Inc. with AI agents.

import java.io.BufferedReader;
import java.io.FileDescriptor;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.Locale;

/**
 * Ground truth for the census: formats each string with the real
 * java.util.Formatter. Reads "id TAB types TAB base64(source) TAB
 * base64(translation)" lines; types is one letter per argument the source
 * passes (S general, I integer, D decimal, C character, L date as a long).
 * Prints "id" then source and translation results for four argument sets,
 * each OK or the simple name of the exception String.format threw:
 * A passes text for %s and an Integer for integers, B a number for %s and
 * an Integer, C text and a Long, D a number and a Long. An app may pass an
 * Int or a Long for %d, and %t or %c accept only one of the two.
 */
public class FormatCheck {
    static Object[] args(String types, boolean numbers, boolean longs) {
        if (types.isEmpty()) {
            return new Object[0];
        }
        String[] t = types.split(",");
        Object[] out = new Object[t.length];
        for (int i = 0; i < t.length; i++) {
            switch (t[i]) {
                case "I": out[i] = longs ? (Object) Long.valueOf(3L) : (Object) Integer.valueOf(3); break;
                case "D": out[i] = Double.valueOf(2.5); break;
                case "C": out[i] = Character.valueOf('x'); break;
                case "L": out[i] = Long.valueOf(1700000000000L); break;
                default: out[i] = numbers ? (Object) Integer.valueOf(7) : (Object) "x";
            }
        }
        return out;
    }

    static String run(String format, Object[] args) {
        try {
            String.format(Locale.ROOT, format, args);
            return "OK";
        } catch (RuntimeException e) {
            return e.getClass().getSimpleName();
        }
    }

    public static void main(String[] argv) throws IOException {
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
        PrintStream out = new PrintStream(new FileOutputStream(FileDescriptor.out), false, "UTF-8");
        Base64.Decoder b64 = Base64.getDecoder();
        String line;
        while ((line = in.readLine()) != null) {
            String[] f = line.split("\t", -1);
            String source = new String(b64.decode(f[2]), StandardCharsets.UTF_8);
            String target = new String(b64.decode(f[3]), StandardCharsets.UTF_8);
            StringBuilder sb = new StringBuilder(f[0]);
            for (int set = 0; set < 4; set++) {
                Object[] a = args(f[1], (set & 1) == 1, (set & 2) == 2);
                sb.append('\t').append(run(source, a)).append('\t').append(run(target, a));
            }
            out.print(sb.append('\n'));
            out.flush();
        }
    }
}
