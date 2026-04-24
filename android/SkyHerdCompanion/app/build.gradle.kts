plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
}

android {
    namespace = "com.skyherd.companion"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.skyherd.companion"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "1.0.0"

        // DJI SDK API key is read from local.properties at build time.
        // George: add  dji.sdk.api.key=YOUR_KEY_HERE  to local.properties.
        val djiKey = project.findProperty("dji.sdk.api.key") as String? ?: ""
        manifestPlaceholders["DJI_SDK_API_KEY"] = djiKey
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        viewBinding = true
    }

    // DJI SDK requires native libs; packaging rules prevent duplicate .so files.
    packaging {
        jniLibs {
            useLegacyPackaging = true
        }
        resources {
            excludes += setOf(
                "META-INF/DEPENDENCIES",
                "META-INF/LICENSE",
                "META-INF/LICENSE.txt",
                "META-INF/NOTICE",
                "META-INF/NOTICE.txt"
            )
        }
    }
}

dependencies {
    // DJI Mobile SDK V5
    implementation(libs.dji.sdk.v5.aircraft)
    runtimeOnly(libs.dji.sdk.v5.networkImp)

    // HTTP / WebSocket (OkHttp)
    implementation(libs.okhttp)

    // MQTT (Paho)
    implementation(libs.paho.mqtt.android)
    implementation(libs.paho.mqtt.client)

    // Logging
    implementation(libs.slf4j.android)

    // Coroutines
    implementation(libs.kotlinx.coroutines.android)

    // AndroidX
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")

    // ---- Unit tests (Phase 7.2: parity with iOS SafetyGuardTests) ----
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.jetbrains.kotlin:kotlin-test:1.9.22")
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.7.3")
    // org.json ships with Android but is stubbed on host JVM — use the
    // same impl artifact in unit tests.
    testImplementation("org.json:json:20231013")
}
