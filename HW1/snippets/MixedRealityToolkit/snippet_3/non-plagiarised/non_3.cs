using MixedReality.Toolkit.Subsystems;
using UnityEngine;
using UnityEngine.Events;

namespace MixedReality.Toolkit.Examples
{
    using Speech.Windows;

    /// <summary>
    /// Text-to-speech utility that initializes once and then can speak multiple phrases
    /// using a chosen voice and audio source.
    /// </summary>
    [RequireComponent(typeof(AudioSource))]
    [AddComponentMenu("MRTK/Examples/Cached TextToSpeech Speaker")]
    public class CachedTextToSpeechSpeaker : MonoBehaviour
    {
        [SerializeField]
        private AudioSource output;

        [SerializeField]
        private TextToSpeechVoice defaultVoice = TextToSpeechVoice.Default;

        [System.Serializable]
        public class StringUnityEvent : UnityEvent<string> { }

        [field: SerializeField]
        public StringUnityEvent OnInitializationFailed { get; private set; }

        private TextToSpeechSubsystem subsystem;
        private WindowsTextToSpeechSubsystemConfig windowsConfig;
        private bool isInitialized;

        /// <summary>
        /// Call once (e.g., on Start or from a setup button) to bind to the TTS subsystem and config.
        /// </summary>
        public void Initialize()
        {
            if (isInitialized)
            {
                return;
            }

            var tts = XRSubsystemHelpers.GetFirstRunningSubsystem<TextToSpeechSubsystem>();
            if (tts == null)
            {
                FailInit("No TextToSpeechSubsystem instance found. Is MRTK3 configured for text-to-speech?");
                return;
            }

            MRTKProfile profile = MRTKProfile.Instance;
            if (profile == null)
            {
                FailInit("MRTKProfile.Instance is null; cannot retrieve TTS configuration.");
                return;
            }

            if (!profile.TryGetConfigForSubsystem(typeof(WindowsTextToSpeechSubsystem), out BaseSubsystemConfig baseConfig) ||
                baseConfig == null)
            {
                FailInit("Failed to obtain configuration for WindowsTextToSpeechSubsystem.");
                return;
            }

            windowsConfig = baseConfig as WindowsTextToSpeechSubsystemConfig;
            if (windowsConfig == null)
            {
                FailInit("Retrieved configuration is not a WindowsTextToSpeechSubsystemConfig.");
                return;
            }

            subsystem = tts;
            windowsConfig.Voice = defaultVoice;
            isInitialized = true;
        }

        /// <summary>
        /// Speaks a demonstration line using the cached configuration.
        /// </summary>
        public void SpeakDemoLine()
        {
            if (!isInitialized)
            {
                Initialize();
            }

            if (!isInitialized)
            {
                // Initialization failed; error already raised.
                return;
            }

            string line =
                $"You are currently listening to the {windowsConfig.Voice} voice. The sound should appear to be attached to this game object in the scene.";

            subsystem.TrySpeak(line, output);
        }

        private void FailInit(string reason)
        {
            Debug.LogError(reason);
            OnInitializationFailed?.Invoke(reason);
        }
    }
}
