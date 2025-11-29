using MixedReality.Toolkit.Subsystems;
using UnityEngine;
using UnityEngine.Events;

namespace MixedReality.Toolkit.Examples
{
    using Speech.Windows;

    /// <summary>
    /// Plays a short phrase using MRTK's Windows text-to-speech integration.
    /// </summary>
    [RequireComponent(typeof(AudioSource))]
    [AddComponentMenu("MRTK/Examples/Voice Demo Handler")]
    public class VoiceDemoHandler : MonoBehaviour
    {
        [SerializeField]
        [Tooltip("AudioSource used to emit the synthesized voice.")]
        private AudioSource voiceOutput;

        [SerializeField]
        [Tooltip("Voice selection used for the demo phrase.")]
        private TextToSpeechVoice demoVoice = TextToSpeechVoice.Default;

        [System.Serializable]
        public class StringEvent : UnityEvent<string> { }

        [field: SerializeField]
        public StringEvent OnDemoFailed { get; private set; }

        private TextToSpeechSubsystem subsystem;

        public void RunDemo()
        {
            subsystem = XRSubsystemHelpers.GetFirstRunningSubsystem<TextToSpeechSubsystem>();
            if (subsystem == null)
            {
                Fail("No TextToSpeechSubsystem instance found. Is the subsystem enabled in the MRTK profile?");
                return;
            }

            if (!TryGetWindowsConfig(out WindowsTextToSpeechSubsystemConfig config))
            {
                return;
            }

            config.Voice = demoVoice;

            string message =
                $"This is the {config.Voice} voice. Move around the scene and notice that the sound remains anchored to this object.";

            subsystem.TrySpeak(message, voiceOutput);
        }

        private bool TryGetWindowsConfig(out WindowsTextToSpeechSubsystemConfig config)
        {
            config = null;

            MRTKProfile profile = MRTKProfile.Instance;
            if (profile == null)
            {
                Fail("MRTKProfile.Instance returned null; cannot resolve configuration.");
                return false;
            }

            if (!profile.TryGetConfigForSubsystem(typeof(WindowsTextToSpeechSubsystem), out BaseSubsystemConfig baseConfig) ||
                baseConfig == null)
            {
                Fail("Failed to retrieve configuration for WindowsTextToSpeechSubsystem.");
                return false;
            }

            config = baseConfig as WindowsTextToSpeechSubsystemConfig;
            if (config == null)
            {
                Fail("Configuration is not of type WindowsTextToSpeechSubsystemConfig.");
                return false;
            }

            return true;
        }

        private void Fail(string error)
        {
            Debug.LogError(error);
            OnDemoFailed?.Invoke(error);
        }
    }
}
