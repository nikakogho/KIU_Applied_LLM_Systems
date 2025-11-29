using TMPro;
using UnityEngine;
using MixedReality.Toolkit.UX.Experimental;

namespace MixedReality.Toolkit.Examples.Demos
{
    [AddComponentMenu("MRTK/Examples/Virtualized Scroll Rect List Tester")]
    public class VirtualizedScrollRectListTester : MonoBehaviour
    {
        [SerializeField]
        [Tooltip("Drive the list scroll with a simple sine pattern.")]
        private bool enableAutoScroll = true;

        private VirtualizedScrollRectList scrollTarget;
        private float desiredScroll;
        private bool isLerping;

        private readonly string[] sampleWords = { "one", "two", "three", "zebra", "keyboard", "rabbit", "graphite", "ruby" };

        private void Start()
        {
            scrollTarget = GetComponent<VirtualizedScrollRectList>();
            scrollTarget.OnVisible = (item, index) =>
            {
                var texts = item.GetComponentsInChildren<TextMeshProUGUI>();
                for (int t = 0; t < texts.Length; t++)
                {
                    if (texts[t].gameObject.name == "Text")
                    {
                        texts[t].text = $"{index} {sampleWords[index % sampleWords.Length]}";
                    }
                }
            };
        }

        private void Update()
        {
            if (enableAutoScroll)
            {
                float phase = Time.time * 0.5f - Mathf.PI * 0.5f;
                float normalizedScroll = Mathf.Sin(phase) * 0.5f + 0.5f;

                scrollTarget.Scroll = normalizedScroll * scrollTarget.MaxScroll;

                desiredScroll = scrollTarget.Scroll;
                isLerping = false;
            }

            if (isLerping)
            {
                float s = Mathf.Lerp(scrollTarget.Scroll, desiredScroll, 8f * Time.deltaTime);
                scrollTarget.Scroll = s;

                if (Mathf.Abs(scrollTarget.Scroll - desiredScroll) < 0.02f)
                {
                    scrollTarget.Scroll = desiredScroll;
                    isLerping = false;
                }
            }
        }

        public void Next()
        {
            enableAutoScroll = false;
            isLerping = true;

            float block = Mathf.Floor(scrollTarget.Scroll / scrollTarget.RowsOrColumns) * scrollTarget.RowsOrColumns;
            desiredScroll = Mathf.Min(scrollTarget.MaxScroll, block + scrollTarget.TotallyVisibleCount);
        }

        public void Prev()
        {
            enableAutoScroll = false;
            isLerping = true;

            float block = Mathf.Floor(scrollTarget.Scroll / scrollTarget.RowsOrColumns) * scrollTarget.RowsOrColumns;
            desiredScroll = Mathf.Max(0f, block - scrollTarget.TotallyVisibleCount);
        }

        [ContextMenu("Set Item Count 50")]
        public void SetItems50() => scrollTarget.SetItemCount(50);

        [ContextMenu("Set Item Count 200")]
        public void SetItems200() => scrollTarget.SetItemCount(200);
    }
}
