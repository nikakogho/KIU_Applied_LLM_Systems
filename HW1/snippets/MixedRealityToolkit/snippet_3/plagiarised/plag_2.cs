using MixedReality.Toolkit.Subsystems;
using UnityEngine;
using UnityEngine.Events;

namespace MixedReality.Toolkit.Examples
{
    using Speech.Windows;

    /// <summary>
    /// Simple utility that speaks a line of text using the configured voice.
    /// </summary>
    [RequireComponent(typeof(AudioSource))]
    [AddComponentMenu("MRTK/Examples/Simple TextToSpeech")]
    public class SimpleTextToSpeech : MonoBehaviour
    {
        [SerializeField]
        [Tooltip("Audio source where synthesized audio will be played.")]
        private AudioSource outputSource;

        [SerializeField]
        [Tooltip("Voice to use for generating the demo line.")]
        private TextToSpeechVoice selectedVoice = TextToSpeechVoice.Default;

        [System.Serializable]
        public class StringEvent : UnityEvent<string> { }

        [field: SerializeField]
        public StringEvent OnError { get; private set; }

        private TextToSpeechSubsystem tts;

        /// <summary>
        /// Called (e.g., by a button) to speak a demo line.
        /// </summary>
        public void SayDemoLine()
        {
            tts = XRSubsystemHelpers.GetFirstRunningSubsystem<TextToSpeechSubsystem>();
            if (tts == null)
            {
                Report("TextToSpeechSubsystem not running. Verify MRTK3 configuration.");
                return;
            }

            MRTKProfile profile = MRTKProfile.Instance;
            if (profile == null)
            {
                Report("MRTKProfile is missing. Cannot resolve TTS configuration.");
                return;
            }

            if (!profile.TryGetConfigForSubsystem(typeof(WindowsTextToSpeechSubsystem), out BaseSubsystemConfig config) ||
                config == null)
            {
                Report("Could not obtain config for WindowsTextToSpeechSubsystem.");
                return;
            }

            if (config is WindowsTextToSpeechSubsystemConfig windowsCfg)
            {
                windowsCfg.Voice = selectedVoice;

                var text =
                    $"You are currently hearing the {windowsCfg.Voice} voice. The audio should sound like it is attached to this object in the scene.";

                tts.TrySpeak(text, outputSource);
            }
        }

        private void Report(string msg)
        {
            Debug.LogError(msg);
            OnError?.Invoke(msg);
        }
    }
}
