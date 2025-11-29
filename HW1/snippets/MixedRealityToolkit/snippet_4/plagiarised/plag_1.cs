using TMPro;
using UnityEngine;
using MixedReality.Toolkit.UX.Experimental;

namespace MixedReality.Toolkit.Examples.Demos
{
    [AddComponentMenu("MRTK/Examples/Virtualized Scroll Rect List Tester")]
    public class VirtualizedScrollRectListTester : MonoBehaviour
    {
        [SerializeField]
        [Tooltip("Automatically scrolls the list up and down with a sine wave.")]
        private bool autoSinScroll = true;

        private VirtualizedScrollRectList scrollList;
        private float targetScrollValue;
        private bool isAnimating;

        private readonly string[] words = { "one", "two", "three", "zebra", "keyboard", "rabbit", "graphite", "ruby" };

        private void Start()
        {
            scrollList = GetComponent<VirtualizedScrollRectList>();
            scrollList.OnVisible = (go, index) =>
            {
                foreach (var text in go.GetComponentsInChildren<TextMeshProUGUI>())
                {
                    if (text.gameObject.name == "Text")
                    {
                        text.text = $"{index} {words[index % words.Length]}";
                    }
                }
            };
        }

        private void Update()
        {
            if (autoSinScroll)
            {
                // normalized [0,1] sine wave
                float t = Time.time * 0.5f - Mathf.PI * 0.5f;
                float normalized = (Mathf.Sin(t) * 0.5f) + 0.5f;

                scrollList.Scroll = normalized * scrollList.MaxScroll;
                targetScrollValue = scrollList.Scroll;
                isAnimating = false;
            }

            if (isAnimating)
            {
                float newScroll = Mathf.Lerp(scrollList.Scroll, targetScrollValue, 8f * Time.deltaTime);
                scrollList.Scroll = newScroll;

                if (Mathf.Abs(scrollList.Scroll - targetScrollValue) < 0.02f)
                {
                    scrollList.Scroll = targetScrollValue;
                    isAnimating = false;
                }
            }
        }

        public void Next()
        {
            autoSinScroll = false;
            isAnimating = true;

            float pageStart = Mathf.Floor(scrollList.Scroll / scrollList.RowsOrColumns) * scrollList.RowsOrColumns;
            targetScrollValue = Mathf.Min(scrollList.MaxScroll, pageStart + scrollList.TotallyVisibleCount);
        }

        public void Prev()
        {
            autoSinScroll = false;
            isAnimating = true;

            float pageStart = Mathf.Floor(scrollList.Scroll / scrollList.RowsOrColumns) * scrollList.RowsOrColumns;
            targetScrollValue = Mathf.Max(0f, pageStart - scrollList.TotallyVisibleCount);
        }

        [ContextMenu("Set Item Count 50")]
        public void TestItemCount1() => scrollList.SetItemCount(50);

        [ContextMenu("Set Item Count 200")]
        public void TestItemCount2() => scrollList.SetItemCount(200);
    }
}
