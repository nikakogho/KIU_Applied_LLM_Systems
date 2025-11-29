using TMPro;
using UnityEngine;
using MixedReality.Toolkit.UX.Experimental;

namespace MixedReality.Toolkit.Examples.Demos
{
    /// <summary>
    /// Example controller that:
    /// - assigns labels to visible items,
    /// - supports auto-scrolling using a sine wave,
    /// - and exposes next/previous page commands.
    /// </summary>
    [AddComponentMenu("MRTK/Examples/Virtualized Scroll Rect Hybrid Controller")]
    public class VirtualizedScrollRectHybridController : MonoBehaviour
    {
        [SerializeField]
        private bool autoScrollEnabled = true;

        [SerializeField]
        private float sineFrequency = 0.5f;

        [SerializeField]
        private float pageTransitionSpeed = 6f;

        private VirtualizedScrollRectList list;
        private bool inPageTransition;
        private float targetScrollPosition;

        private readonly string[] wordBank = { "one", "two", "three", "zebra", "keyboard", "rabbit", "graphite", "ruby" };

        private void Start()
        {
            list = GetComponent<VirtualizedScrollRectList>();
            list.OnVisible = AssignLabel;
        }

        private void AssignLabel(GameObject row, int index)
        {
            // Just grab the first TextMeshProUGUI under the row.
            var label = row.GetComponentInChildren<TextMeshProUGUI>();
            if (label != null)
            {
                int wordIndex = index % wordBank.Length;
                label.text = $"{index} {wordBank[wordIndex]}";
            }
        }

        private void Update()
        {
            if (autoScrollEnabled)
            {
                float normalized = 0.5f * (Mathf.Sin(Time.time * sineFrequency) + 1f);
                list.Scroll = normalized * list.MaxScroll;

                inPageTransition = false;
                targetScrollPosition = list.Scroll;
            }
            else if (inPageTransition)
            {
                list.Scroll = Mathf.Lerp(list.Scroll, targetScrollPosition, pageTransitionSpeed * Time.deltaTime);

                if (Mathf.Abs(list.Scroll - targetScrollPosition) <= 0.02f)
                {
                    list.Scroll = targetScrollPosition;
                    inPageTransition = false;
                }
            }
        }

        public void NextPage()
        {
            autoScrollEnabled = false;
            inPageTransition = true;

            float pageSpan = list.TotallyVisibleCount;
            float current = Mathf.Floor(list.Scroll / pageSpan) * pageSpan;
            targetScrollPosition = Mathf.Clamp(current + pageSpan, 0f, list.MaxScroll);
        }

        public void PreviousPage()
        {
            autoScrollEnabled = false;
            inPageTransition = true;

            float pageSpan = list.TotallyVisibleCount;
            float current = Mathf.Floor(list.Scroll / pageSpan) * pageSpan;
            targetScrollPosition = Mathf.Clamp(current - pageSpan, 0f, list.MaxScroll);
        }

        [ContextMenu("Use 50 items")]
        public void Configure50() => list.SetItemCount(50);

        [ContextMenu("Use 200 items")]
        public void Configure200() => list.SetItemCount(200);
    }
}
