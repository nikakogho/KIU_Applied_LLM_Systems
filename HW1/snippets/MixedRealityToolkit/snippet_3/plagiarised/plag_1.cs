using MixedReality.Toolkit.Subsystems;
using UnityEngine;
using UnityEngine.Events;

namespace MixedReality.Toolkit.Examples
{
    using Speech.Windows;

    /// <summary>
    /// Plays a short sample phrase using the MRTK text-to-speech subsystem.
    /// </summary>
    [RequireComponent(typeof(AudioSource))]
    [AddComponentMenu("MRTK/Examples/Object Speech Demo")]
    public class ObjectSpeechDemo : MonoBehaviour
    {
        [SerializeField]
        [Tooltip("AudioSource used to output synthesized speech.")]
        private AudioSource speaker;

        [SerializeField]
        [Tooltip("Voice profile used for speech synthesis. Set to Other for non en-US voices.")]
        private TextToSpeechVoice voiceProfile;

        [System.Serializable]
        public class StringEvent : UnityEvent<string> { }

        [field: SerializeField]
        public StringEvent OnSpeechFailed { get; private set; }

        private TextToSpeechSubsystem ttsSubsystem;

        /// <summary>
        /// Entry point for triggering the demo phrase.
        /// </summary>
        public void PlaySample()
        {
            // Locate a running TTS subsystem.
            ttsSubsystem = XRSubsystemHelpers.GetFirstRunningSubsystem<TextToSpeechSubsystem>();
            if (ttsSubsystem == null)
            {
                RaiseError("No running TextToSpeechSubsystem found. Check MRTK3 settings.");
                return;
            }

            // Grab the active MRTK profile.
            var profile = MRTKProfile.Instance;
            if (profile == null)
            {
                RaiseError("MRTKProfile.Instance is null. Cannot access TTS configuration.");
                return;
            }

            // Look up the configuration for WindowsTextToSpeechSubsystem.
            if (!profile.TryGetConfigForSubsystem(typeof(WindowsTextToSpeechSubsystem), out BaseSubsystemConfig cfg) ||
                cfg == null)
            {
                RaiseError("Failed to retrieve configuration for WindowsTextToSpeechSubsystem.");
                return;
            }

            if (cfg is WindowsTextToSpeechSubsystemConfig windowsConfig)
            {
                // Apply the chosen voice and synthesize a simple description.
                windowsConfig.Voice = voiceProfile;

                string line =
                    $"This is the {windowsConfig.Voice} voice. The sound should be anchored to this object, so try walking around it.";

                ttsSubsystem.TrySpeak(line, speaker);
            }
        }

        private void RaiseError(string message)
        {
            Debug.LogError(message);
            OnSpeechFailed?.Invoke(message);
        }
    }
}
