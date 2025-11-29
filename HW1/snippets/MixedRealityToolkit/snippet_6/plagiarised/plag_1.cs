using MixedReality.Toolkit.SpatialManipulation;
using MixedReality.Toolkit.UX;
using System.Collections;
using System.Text;
using TMPro;
using UnityEngine;

namespace MixedReality.Toolkit.Examples.Demos
{
    public class BoundsControlRuntimeExample : MonoBehaviour
    {
        [SerializeField]
        private TextMeshPro statusLabel;

        [SerializeField]
        private Material cubeMaterial;

        [SerializeField]
        private GameObject boundsVisualPrefab;

        [SerializeField]
        private Transform parentForCubes;

        private bool advanceRequested;
        private readonly Vector3 initialCubePosition = new Vector3(0, 1.2f, 2);
        private readonly Vector3 initialCubeSize = new Vector3(0.5f, 0.5f, 0.5f);
        private BoundsControl activeBoundsControl;
        private readonly StringBuilder sb = new StringBuilder();

        protected virtual void Start()
        {
            StartCoroutine(RunSequence());
        }

        private void UpdateStatus(string status)
        {
            Debug.Assert(statusLabel != null, "statusLabel should not be null");
            sb.Clear();
            sb.AppendLine(status);
            sb.AppendLine("Press Next or say 'next' to continue");
            statusLabel.text = sb.ToString();
        }

        private IEnumerator RunSequence()
        {
            while (true)
            {
                // Single cube demo
                var cube = GameObject.CreatePrimitive(PrimitiveType.Cube);
                Debug.Assert(cubeMaterial != null);
                cube.GetComponent<MeshRenderer>().material = cubeMaterial;
                cube.transform.SetParent(parentForCubes == null ? transform : parentForCubes);
                cube.transform.position = initialCubePosition;
                cube.transform.localScale = initialCubeSize;

                UpdateStatus("Instantiate BoundsControl");
                activeBoundsControl = SetupBoundsControl(cube);
                yield return WaitForAdvance();

                UpdateStatus("Set Target bounds override");
                GameObject overrideObject = new GameObject("overrideBounds");
                overrideObject.transform.position = new Vector3(0.8f, 0.8f, 1.8f);
                var overrideCollider = overrideObject.AddComponent<BoxCollider>();
                overrideCollider.size = new Vector3(0.162f, 0.1f, 1f);
                activeBoundsControl.OverrideBounds = true;
                activeBoundsControl.BoundsOverride = overrideCollider.transform;
                yield return WaitForAdvance();

                UpdateStatus("Change target bounds override size");
                overrideCollider.size = new Vector3(0.5f, 0.1f, 1f);
                activeBoundsControl.RecomputeBounds();
                yield return WaitForAdvance();

                UpdateStatus("RotateAnchor Object Origin");
                activeBoundsControl.RotateAnchor = RotateAnchorType.ObjectOrigin;
                yield return WaitForAdvance();

                UpdateStatus("RotateAnchor Bounds Center");
                activeBoundsControl.RotateAnchor = RotateAnchorType.BoundsCenter;
                yield return WaitForAdvance();

                UpdateStatus("ScaleAnchor Opposite Corner");
                activeBoundsControl.ScaleAnchor = ScaleAnchorType.OppositeCorner;
                yield return WaitForAdvance();

                UpdateStatus("ScaleAnchor Bounds Center");
                activeBoundsControl.ScaleAnchor = ScaleAnchorType.BoundsCenter;
                yield return WaitForAdvance();

                UpdateStatus("Remove target bounds override");
                activeBoundsControl.OverrideBounds = false;
                activeBoundsControl.BoundsOverride = null;
                Destroy(overrideObject);
                yield return WaitForAdvance();

                UpdateStatus("FlattenAuto");
                activeBoundsControl.FlattenMode = FlattenMode.Auto;
                yield return WaitForAdvance();

                UpdateStatus("FlattenAlways");
                activeBoundsControl.FlattenMode = FlattenMode.Always;
                yield return WaitForAdvance();

                UpdateStatus("FlattenNever");
                activeBoundsControl.FlattenMode = FlattenMode.Never;
                yield return WaitForAdvance();

                UpdateStatus("BoxPadding 0.2f");
                activeBoundsControl.BoundsPadding = 0.2f;
                yield return WaitForAdvance();

                UpdateStatus("BoxPadding 0");
                activeBoundsControl.BoundsPadding = 0f;
                yield return WaitForAdvance();

                UpdateStatus("Scale X and update rig");
                cube.transform.localScale = new Vector3(1f, 0.5f, 0.5f);
                yield return WaitForAdvance();

                UpdateStatus("Rotate 20 degrees and update rig");
                cube.transform.localRotation = Quaternion.Euler(0f, 20f, 0f);
                yield return WaitForAdvance();

                UpdateStatus("HandleType None");
                activeBoundsControl.EnabledHandles = HandleType.None;
                yield return WaitForAdvance();

                UpdateStatus("HandleType Rotation");
                activeBoundsControl.EnabledHandles = HandleType.Rotation;
                yield return WaitForAdvance();

                UpdateStatus("HandleType Scale");
                activeBoundsControl.EnabledHandles = HandleType.Scale;
                yield return WaitForAdvance();

                UpdateStatus("HandleType Translation");
                activeBoundsControl.EnabledHandles = HandleType.Translation;
                yield return WaitForAdvance();

                Destroy(cube);

                // Multi-child setup
                UpdateStatus("Many children");

                GameObject multiRoot = new GameObject("multiRoot");
                Vector3 forwardOffset = Vector3.forward * 0.5f;
                multiRoot.transform.position = initialCubePosition + forwardOffset;

                Transform lastParent = null;
                const int childCount = 10;

                for (int i = 0; i < childCount; i++)
                {
                    var childCube = GameObject.CreatePrimitive(PrimitiveType.Cube);
                    childCube.GetComponent<MeshRenderer>().material = cubeMaterial;
                    childCube.transform.localPosition = Random.insideUnitSphere + initialCubePosition + forwardOffset;
                    childCube.transform.rotation = Quaternion.Euler(Random.insideUnitSphere * 360f);
                    childCube.transform.parent = (lastParent != null) ? lastParent : multiRoot.transform;
                    float baseScale = lastParent == null ? 0.1f : 1f;
                    childCube.transform.localScale = new Vector3(baseScale, baseScale, baseScale);
                    lastParent = childCube.transform;
                }

                activeBoundsControl = SetupBoundsControl(multiRoot);

                UpdateStatus("Randomize Child Scale for skewing");
                yield return WaitForAdvance();

                multiRoot.transform.position += Vector3.forward * 200f;

                var walkTransform = multiRoot.transform;
                while (walkTransform.childCount > 0)
                {
                    walkTransform = walkTransform.GetChild(0);
                    float baseScale = lastParent == null ? 0.1f : 1f;
                    walkTransform.localScale = new Vector3(
                        baseScale * Random.Range(0.5f, 2f),
                        baseScale * Random.Range(0.5f, 2f),
                        baseScale * Random.Range(0.5f, 2f));
                }

                activeBoundsControl.RecomputeBounds();

                UpdateStatus("Delete GameObject");
                yield return WaitForAdvance();

                Destroy(multiRoot);

                UpdateStatus("Done!");
                yield return WaitForAdvance();
            }
        }

        private BoundsControl SetupBoundsControl(GameObject target)
        {
            target.AddComponent<ConstraintManager>();
            target.AddComponent<ObjectManipulator>();
            var bounds = target.AddComponent<BoundsControl>();
            bounds.BoundsVisualsPrefab = boundsVisualPrefab;
            bounds.HandlesActive = true;
            bounds.DragToggleThreshold = 0.02f;
            target.AddComponent<UGUIInputAdapterDraggable>();
            return bounds;
        }

        private IEnumerator WaitForAdvance()
        {
            while (!advanceRequested)
            {
                yield return null;
            }

            advanceRequested = false;
            yield break;
        }

        public void OnShouldAdvanceSequence()
        {
            advanceRequested = true;
        }
    }
}
