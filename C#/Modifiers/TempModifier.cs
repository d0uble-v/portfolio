using System.Collections;
using UnityEngine;


namespace Sourcery.Stats
{
    public class TempModifier : Modifier
    {
        public new FloatingValue target;


        public readonly float duration;

        /// <summary>
        /// Reference to our coroutine in case it needs to be stopped on demand.
        /// </summary>
        protected Coroutine coroutine;


        public TempModifier(FloatingValue target, float amount, float duration, object origin, int priority = 0) : base(target, amount, origin, priority)
        {
            this.duration = duration;
        }


        protected virtual IEnumerator Expire()
        {
            yield return new WaitForSeconds(duration);
            target.RemoveModifier(this);
        }


        /// <summary>
        /// Schedules this modifier's expiry coroutine.
        /// </summary>
        public override void Activate()
        {
            if (coroutine == null)
            {
                coroutine = target.stat.statSystem.StartCoroutine(Expire());
                Debug.Log("Modifier expiry has been scheduled.");
            }
            else Debug.Log("Modifier expiry was already scheduled.");
        }


        /// <summary>
        /// Stops this modifier's expiry coroutine if active.
        /// </summary>
        public override void Deactivate()
        {
            if (coroutine != null)
            {
                target.stat.statSystem.StopCoroutine(coroutine);
                coroutine = null;
                Debug.Log("Modifier has been forced to expire.");
            }
            else Debug.Log("Modifier was already expired.");
        }
    }
}