using MixedReality.Toolkit.Subsystems;
using UnityEngine;
using UnityEngine.Events;

namespace MixedReality.Toolkit.Examples
{
    using Speech.Windows;

    /// <summary>
    /// Provides a one-shot API to trigger a short spoken description using the MRTK text-to-speech subsystem.
    /// This class uses a straight-line pipeline with early returns on failure.
    /// </summary>
    [RequireComponent(typeof(AudioSource))]
    [AddComponentMenu("MRTK/Examples/One Shot TextToSpeech")]
    public class OneShotTextToSpeech : MonoBehaviour
    {
        [SerializeField]
        private AudioSource speaker;

        [SerializeField]
        private TextToSpeechVoice selectedVoice = TextToSpeechVoice.Default;

        [System.Serializable]
        public class StringUnityEvent : UnityEvent<string> { }

        [field: SerializeField]
        public StringUnityEvent OnSpeakFailed { get; private set; }

        public void TriggerSpeech()
        {
            var subsystem = XRSubsystemHelpers.GetFirstRunningSubsystem<TextToSpeechSubsystem>();
            if (subsystem == null)
            {
                EmitError("Text-to-speech subsystem is not running.");
                return;
            }

            MRTKProfile profile = MRTKProfile.Instance;
            if (profile == null)
            {
                EmitError("MRTK profile is missing; cannot access TTS configuration.");
                return;
            }

            if (!profile.TryGetConfigForSubsystem(typeof(WindowsTextToSpeechSubsystem), out BaseSubsystemConfig baseConfig) ||
                baseConfig == null)
            {
                EmitError("TTS configuration could not be obtained for WindowsTextToSpeechSubsystem.");
                return;
            }

            if (!(baseConfig is WindowsTextToSpeechSubsystemConfig winConfig))
            {
                EmitError("Unexpected configuration type encountered for Windows text-to-speech.");
                return;
            }

            winConfig.Voice = selectedVoice;

            string content = DescribeVoice(selectedVoice);
            subsystem.TrySpeak(content, speaker);
        }

        private string DescribeVoice(TextToSpeechVoice voice)
        {
            // You could make this smarter later (different messages per voice).
            switch (voice)
            {
                case TextToSpeechVoice.Female:
                    return "You are listening to the female voice profile, spoken from the object you interacted with.";
                case TextToSpeechVoice.Male:
                    return "This is the male voice profile. Notice how the sound is anchored at the object in the scene.";
                default:
                    return $"This is the {voice} voice. Walk around the scene to explore how the audio follows this object.";
            }
        }

        private void EmitError(string error)
        {
            Debug.LogError(error);
            OnSpeakFailed?.Invoke(error);
        }
    }
}
