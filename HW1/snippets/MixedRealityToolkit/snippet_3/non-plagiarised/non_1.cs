using MixedReality.Toolkit.Subsystems;
using UnityEngine;
using UnityEngine.Events;

namespace MixedReality.Toolkit.Examples
{
    using Speech.Windows;

    /// <summary>
    /// Component that plays a short demo phrase using the configured text-to-speech subsystem.
    /// Responsible for locating the subsystem, obtaining the Windows TTS configuration,
    /// and forwarding errors via a UnityEvent.
    /// </summary>
    [RequireComponent(typeof(AudioSource))]
    [AddComponentMenu("MRTK/Examples/Object Voice Demo")]
    public class ObjectVoiceDemo : MonoBehaviour
    {
        [SerializeField]
        [Tooltip("AudioSource used to emit synthesized speech from this object.")]
        private AudioSource outputSource;

        [SerializeField]
        [Tooltip("Desired voice to use when synthesizing speech.")]
        private TextToSpeechVoice demoVoice = TextToSpeechVoice.Default;

        [System.Serializable]
        public class StringUnityEvent : UnityEvent<string> { }

        [field: SerializeField]
        public StringUnityEvent OnError { get; private set; }

        private TextToSpeechSubsystem ttsSubsystem;

        /// <summary>
        /// Invoked (e.g., by a button) to say a demo phrase from this object's position.
        /// </summary>
        public void PlayDemo()
        {
            if (!TryAcquireSubsystem(out ttsSubsystem))
            {
                return;
            }

            if (!TryGetWindowsConfig(out WindowsTextToSpeechSubsystemConfig config))
            {
                return;
            }

            // Apply the selected voice and synthesize a sample message.
            config.Voice = demoVoice;

            string phrase = BuildDemoPhrase(config.Voice);
            ttsSubsystem.TrySpeak(phrase, outputSource);
        }

        private bool TryAcquireSubsystem(out TextToSpeechSubsystem subsystem)
        {
            subsystem = XRSubsystemHelpers.GetFirstRunningSubsystem<TextToSpeechSubsystem>();
            if (subsystem == null)
            {
                RaiseError(
                    "No running TextToSpeechSubsystem found. Verify MRTK3 configuration and platform support.");
                return false;
            }

            return true;
        }

        private bool TryGetWindowsConfig(out WindowsTextToSpeechSubsystemConfig config)
        {
            config = null;

            MRTKProfile profile = MRTKProfile.Instance;
            if (profile == null)
            {
                RaiseError("MRTKProfile.Instance was null. Cannot locate text-to-speech configuration.");
                return false;
            }

            if (!profile.TryGetConfigForSubsystem(typeof(WindowsTextToSpeechSubsystem), out BaseSubsystemConfig baseConfig) ||
                baseConfig == null)
            {
                RaiseError($"Could not locate configuration for subsystem {nameof(WindowsTextToSpeechSubsystem)}.");
                return false;
            }

            config = baseConfig as WindowsTextToSpeechSubsystemConfig;
            if (config == null)
            {
                RaiseError("Retrieved configuration was not a WindowsTextToSpeechSubsystemConfig.");
                return false;
            }

            return true;
        }

        private string BuildDemoPhrase(TextToSpeechVoice voice)
        {
            return
                $"You are now hearing the {voice} voice. The sound should appear to come from this object in the scene, so try moving around it to experience the spatial audio.";
        }

        private void RaiseError(string message)
        {
            Debug.LogError(message);
            OnError?.Invoke(message);
        }
    }
}
