# Règles Proguard / R8 pour Santé DZ / Medizy
# Préserver les liaisons natives SQLite FTS5/R-Tree et l'interface FFI Flutter

-keep class io.flutter.** { *; }
-keep class io.flutter.plugin.** { *; }
-keep class com.tekartik.sqflite.** { *; }
-keep class org.sqlite.** { *; }

-keepclasseswithmembernames class * {
    native <methods>;
}

-keepclassmembers class * {
    native <methods>;
}

-keepattributes *Annotation*,EnclosingMethod,Signature,InnerClasses,SourceFile,LineNumberTable
-dontwarn okio.**
-dontwarn javax.annotation.**
