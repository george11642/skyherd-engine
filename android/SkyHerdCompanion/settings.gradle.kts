pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
        // DJI SDK Maven repository
        maven { url = uri("https://sdk-forum.dji.net/nexus/content/repositories/releases/") }
        maven { url = uri("https://sdk-forum.dji.net/nexus/content/repositories/snapshots/") }
    }
}

rootProject.name = "SkyHerdCompanion"
include(":app")
