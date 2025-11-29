using MixedReality.Toolkit.SpatialManipulation;
using MixedReality.Toolkit.UX;
using System;
using System.Collections;
using System.Text;
using TMPro;
using UnityEngine;

namespace MixedReality.Toolkit.Examples.Demos
{
    public class BoundsControlStepRunner : MonoBehaviour
    {
        [SerializeField]
        private TextMeshPro statusText;

        [SerializeField]
        private Material cubeMaterial;

        [SerializeField]
        private GameObject boundsVisualPrefab;

        [SerializeField]
        private Transform cubeParent;

        private bool advance;
        private BoundsControl currentBounds;
        private readonly Vector3 cubePosition = new Vector3(0, 1.2f, 2);
        private readonly Vector3 cubeSize = new Vector3(0.5f, 0.5f, 0.5f);
        private readonly StringBuilder builder = new StringBuilder();

        private void Start()
        {
            StartCoroutine(Sequence());
        }

        private void SetStatus(string status)
        {
            builder.Clear();
            builder.AppendLine(status);
            builder.AppendLine("Click Next or say 'next' to continue.");
            statusText.text = builder.ToString();
        }

        private IEnumerator RunStep(string label, Action action)
        {
            SetStatus(label);
            action?.Invoke();
            while (!advance)
            {
                yield return null;
            }
            advance = false;
        }

        private IEnumerator Sequence()
        {
            while (true)
            {
                // Single cube scenario
                GameObject cube = CreateCube(cubePosition, cubeSize);
                currentBounds = CreateBoundsControl(cube);

                yield return RunStep("Instantiate BoundsControl", () => { });

                GameObject overrideRoot = null;
                BoxCollider overrideCollider = null;

                yield return RunStep("Set Target bounds override", () =>
                {
                    overrideRoot = new GameObject("OverrideBounds");
                    overrideRoot.transform.position = new Vector3(0.8f, 0.8f, 1.8f);
                    overrideCollider = overrideRoot.AddComponent<BoxCollider>();
                    overrideCollider.size = new Vector3(0.162f, 0.1f, 1f);
                    currentBounds.OverrideBounds = true;
                    currentBounds.BoundsOverride = overrideCollider.transform;
                });

                yield return RunStep("Change target bounds override size", () =>
                {
                    overrideCollider.size = new Vector3(0.5f, 0.1f, 1f);
                    currentBounds.RecomputeBounds();
                });

                yield return RunStep("RotateAnchor Object Origin", () =>
                {
                    currentBounds.RotateAnchor = RotateAnchorType.ObjectOrigin;
                });

                yield return RunStep("RotateAnchor Bounds Center", () =>
                {
                    currentBounds.RotateAnchor = RotateAnchorType.BoundsCenter;
                });

                yield return RunStep("ScaleAnchor Opposite Corner", () =>
                {
                    currentBounds.ScaleAnchor = ScaleAnchorType.OppositeCorner;
                });

                yield return RunStep("ScaleAnchor Bounds Center", () =>
                {
                    currentBounds.ScaleAnchor = ScaleAnchorType.BoundsCenter;
                });

                yield return RunStep("Remove target bounds override", () =>
                {
                    currentBounds.OverrideBounds = false;
                    currentBounds.BoundsOverride = null;
                    Destroy(overrideRoot);
                });

                yield return RunStep("FlattenAuto", () =>
                {
                    currentBounds.FlattenMode = FlattenMode.Auto;
                });

                yield return RunStep("FlattenAlways", () =>
                {
                    currentBounds.FlattenMode = FlattenMode.Always;
                });

                yield return RunStep("FlattenNever", () =>
                {
                    currentBounds.FlattenMode = FlattenMode.Never;
                });

                yield return RunStep("BoxPadding 0.2f", () =>
                {
                    currentBounds.BoundsPadding = 0.2f;
                });

                yield return RunStep("BoxPadding 0", () =>
                {
                    currentBounds.BoundsPadding = 0f;
                });

                yield return RunStep("Scale X and update rig", () =>
                {
                    cube.transform.localScale = new Vector3(1f, 0.5f, 0.5f);
                });

                yield return RunStep("Rotate 20 degrees and update rig", () =>
                {
                    cube.transform.localRotation = Quaternion.Euler(0f, 20f, 0f);
                });

                yield return RunStep("HandleType None", () =>
                {
                    currentBounds.EnabledHandles = HandleType.None;
                });

                yield return RunStep("HandleType Rotation", () =>
                {
                    currentBounds.EnabledHandles = HandleType.Rotation;
                });

                yield return RunStep("HandleType Scale", () =>
                {
                    currentBounds.EnabledHandles = HandleType.Scale;
                });

                yield return RunStep("HandleType Translation", () =>
                {
                    currentBounds.EnabledHandles = HandleType.Translation;
                });

                Destroy(cube);

                // Multi-root scenario
                GameObject multiRoot = null;
                Transform lastParent = null;

                yield return RunStep("Many children", () =>
                {
                    multiRoot = new GameObject("multiRoot");
                    Vector3 forwardOffset = Vector3.forward * 0.5f;
                    multiRoot.transform.position = cubePosition + forwardOffset;

                    int numCubes = 10;
                    for (int i = 0; i < numCubes; i++)
                    {
                        var child = GameObject.CreatePrimitive(PrimitiveType.Cube);
                        child.GetComponent<MeshRenderer>().material = cubeMaterial;
                        child.transform.localPosition = Random.insideUnitSphere + cubePosition + forwardOffset;
                        child.transform.rotation = Quaternion.Euler(Random.insideUnitSphere * 360f);
                        child.transform.parent = lastParent == null ? multiRoot.transform : lastParent;
                        float baseScale = lastParent == null ? 0.1f : 1f;
                        child.transform.localScale = Vector3.one * baseScale;
                        lastParent = child.transform;
                    }

                    currentBounds = CreateBoundsControl(multiRoot);
                });

                yield return RunStep("Randomize Child Scale for skewing", () =>
                {
                    multiRoot.transform.position += Vector3.forward * 200f;
                    var current = multiRoot.transform;
                    while (current.childCount > 0)
                    {
                        current = current.GetChild(0);
                        float baseScale = lastParent == null ? 0.1f : 1f;
                        current.localScale = new Vector3(
                            baseScale * Random.Range(0.5f, 2f),
                            baseScale * Random.Range(0.5f, 2f),
                            baseScale * Random.Range(0.5f, 2f));
                    }

                    currentBounds.RecomputeBounds();
                });

                yield return RunStep("Delete GameObject", () =>
                {
                    Destroy(multiRoot);
                });

                yield return RunStep("Done!", () => { });
            }
        }

        private GameObject CreateCube(Vector3 position, Vector3 size)
        {
            var cube = GameObject.CreatePrimitive(PrimitiveType.Cube);
            cube.GetComponent<MeshRenderer>().material = cubeMaterial;
            cube.transform.position = position;
            cube.transform.localScale = size;
            cube.transform.SetParent(cubeParent == null ? transform : cubeParent);
            return cube;
        }

        private BoundsControl CreateBoundsControl(GameObject target)
        {
            target.AddComponent<ConstraintManager>();
            target.AddComponent<ObjectManipulator>();
            var bc = target.AddComponent<BoundsControl>();
            bc.BoundsVisualsPrefab = boundsVisualPrefab;
            bc.HandlesActive = true;
            bc.DragToggleThreshold = 0.02f;
            target.AddComponent<UGUIInputAdapterDraggable>();
            return bc;
        }

        public void OnShouldAdvanceSequence()
        {
            advance = true;
        }
    }
}
